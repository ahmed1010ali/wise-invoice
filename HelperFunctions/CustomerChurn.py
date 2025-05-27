from HelperFunctions.Libraries import *

query="""WITH base_sales AS (
    SELECT
        s.customerid,
        c.name,
        EXTRACT(YEAR FROM s.date) AS year,
        EXTRACT(QUARTER FROM s.date) AS quarter,
        COUNT(*) AS total_sales,
        SUM(s.payout) AS total_payout,
        MAX(s.date) AS last_sale_date,
        COUNT(DISTINCT s.salespersonid) AS num_salespeople,
        COUNT(DISTINCT s.brandid) AS num_brands
    FROM sales s
    JOIN customers c ON s.customerid = c.customerid
    WHERE s.date >= CURRENT_DATE - INTERVAL '5 years'
    GROUP BY s.customerid, c.name, EXTRACT(YEAR FROM s.date), EXTRACT(QUARTER FROM s.date)
),
lagged_sales AS (
    SELECT *,
        LAG(total_payout) OVER (PARTITION BY customerid ORDER BY year, quarter) AS prev_payout
    FROM base_sales
)
SELECT
    customerid,
    name,
    year,
    quarter,
    total_sales,
    total_payout,
    ROUND(total_payout::numeric / NULLIF(total_sales, 0), 2) AS avg_payout_per_transaction,
    last_sale_date,
    num_salespeople,
    num_brands,
    prev_payout,
    ROUND(
        CASE
            WHEN prev_payout IS NULL OR prev_payout = 0 THEN NULL
            ELSE ((total_payout - prev_payout) / prev_payout) * 100
        END, 2
    ) AS payout_growth_rate_percent,
    ROUND(
        CASE
            WHEN prev_payout IS NULL OR prev_payout = 0 THEN NULL
            ELSE ((prev_payout - total_payout) / prev_payout) * 100
        END, 2
    ) AS payout_drop_percent
FROM lagged_sales
ORDER BY customerid, year, quarter
"""

data = supabase.rpc("execute_sql", {"sql": query}).execute() # or use REST/SQL endpoint

def preprocess_sales_data(data):
    df = pd.DataFrame(data)
    df['year'] = df['year'].astype(int)
    df['quarter'] = df['quarter'].astype(int)
    df['date_index'] = df['year'] * 4 + df['quarter']
    df = df.sort_values(['customerid', 'date_index'])
    return df

def analyze_churn_logic(data):
    grouped = data.groupby(['customerid', 'name'])
    result = []

    for (customerid, customername), group in grouped:
        group = group.sort_values('date_index')

        payout_drops = group['payout_drop_percent'].dropna()
        brand_changes = group['num_brands'].diff().fillna(0)
        inactivity_periods = group['date_index'].diff().fillna(1)

        long_inactive_count = (inactivity_periods > 2).sum()
        sharp_declines = (payout_drops > 20).sum()
        brand_drop_count = (brand_changes < 0).sum()

        churn_score = min(100, (long_inactive_count * 20) + (sharp_declines * 10) + (brand_drop_count * 10))

        result.append({
            "customerid": customerid,
            "customername": customername,
            "churn_score": churn_score,
            "long_inactivity_count": long_inactive_count,
            "sharp_payout_declines": sharp_declines,
            "brand_drops": brand_drop_count
        })

    return result

from langchain.schema import HumanMessage
# --- Step 4: Use Gemini to Generate Explanations ---
def generate_churn_explanation(customer):
   prompt = f"""
    العميل {customer['customername']} عنده درجة احتمالية مغادرة (churn score) {customer['churn_score']} من 100.

    العوامل اللي لاحظناها:
    - عدد الفترات اللي ما اشتراش فيها لأكتر من ربعين: {customer['long_inactivity_count']}
    - عدد الانخفاضات الحادة في قيمة المشتريات بنسبة أكتر من 20٪: {customer['sharp_payout_declines']}
    - عدد المرات اللي قل فيها عدد العلامات التجارية اللي بيتعامل معاها: {customer['brand_drops']}

    اكتب شرح مختصر باللهجة المصرية، رسمي وعملي، بدون تحيات أو مقدمات دينية، يوضح ليه العميل ده ممكن يغادر، بناءً على البيانات دي.
"""

   try:
        response = llm([HumanMessage(content=prompt)])
        return response.content.strip()
   except Exception as e:
        return f"تعذر توليد الشرح: {e}"

# --- Step 5: Filter & Run ---
def get_churn_warnings_with_gemini(data):
    churn_results = analyze_churn_logic(data)
    warnings = []

    for customer in churn_results:
        if customer['churn_score'] >= 60:
            explanation = generate_churn_explanation(customer)
            warnings.append({
                "customerid": customer['customerid'],
                "customername": customer['customername'],
                "churn_score": customer['churn_score'],
                "explanation": explanation
            })

    return warnings

# --- Step 6: Output Results ---
df_data=preprocess_sales_data(data.data)
churn_warnings = get_churn_warnings_with_gemini(df_data)

for warning in churn_warnings:
    print(f"\nCustomer: {warning['customername']} (Score: {warning['churn_score']})")
    print(f"Explanation: {warning['explanation']}\n")