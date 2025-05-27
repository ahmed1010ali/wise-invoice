from HelperFunctions.Libraries import *

def fetch_data():
    campaigns_data = supabase.table("campaigns").select("*").order("start_date", desc=True).limit(100).execute().data
    campaigns = pd.DataFrame(campaigns_data)

    # Ensure date columns are datetime objects for easier manipulation
    campaigns['start_date'] = pd.to_datetime(campaigns['start_date'])
    # Assuming 'end_date' exists, if not, you might need to add a default duration
    # For example, if campaigns are always 1 month long, you could do:
    # campaigns['end_date'] = campaigns['start_date'] + pd.DateOffset(months=1)
    campaigns['end_date'] = pd.to_datetime(campaigns['end_date'])

    all_sales_data = supabase.table("sales").select("customerid, brandid, payout, date").execute().data
    all_sales = pd.DataFrame(all_sales_data)
    all_sales['date'] = pd.to_datetime(all_sales['date'])

    # Initialize an empty DataFrame to store filtered sales
    filtered_sales = pd.DataFrame()

    for index, campaign in campaigns.iterrows():
        campaign_start = campaign['start_date']
        campaign_end = campaign['end_date']

        # Calculate the one-month window before and after the campaign
        window_start = campaign_start - pd.DateOffset(months=1)
        window_end = campaign_end + pd.DateOffset(months=1)

        # Filter sales for the current campaign's window
        sales_in_window = all_sales[
            (all_sales['date'] >= window_start) &
            (all_sales['date'] <= window_end)
        ].copy() # Use .copy() to avoid SettingWithCopyWarning

        # You might want to add a campaign identifier to these sales if you plan to merge them
        sales_in_window['campaign_id'] = campaign['campaign_id'] # Assuming 'id' is your campaign identifier

        filtered_sales = pd.concat([filtered_sales, sales_in_window], ignore_index=True)

    customers_data = supabase.table("customers").select("customerid, name").execute().data
    customers = pd.DataFrame(customers_data)

    return {
        "campaigns": campaigns,
        "sales": filtered_sales, # Now 'sales' contains only the filtered data
        "customers": customers
    }

def segment_customers(customers_df, sales_df, n_clusters=4):
    # Convert date to datetime objects
    sales_df['date'] = pd.to_datetime(sales_df['date'])

    # Calculate Recency, Frequency, Monetary (RFM)
    snapshot_date = sales_df['date'].max() + pd.Timedelta(days=1)

    rfm_df = sales_df.groupby('customerid').agg(
        Recency=('date', lambda date: (snapshot_date - date.max()).days),
        Frequency=('customerid', 'count'),
        Monetary=('payout', 'sum')
    ).reset_index()

    # Merge RFM with customers_df
    # Ensure customerid column exists in customers_df for merging
    customers_with_rfm = pd.merge(customers_df, rfm_df, on='customerid', how='left')

    # Handle customers with no sales data (they will have NaN in RFM, treat as new/inactive)
    customers_with_rfm['Recency'] = customers_with_rfm['Recency'].fillna(rfm_df['Recency'].max() + 30 if not rfm_df.empty else 90)
    customers_with_rfm['Frequency'] = customers_with_rfm['Frequency'].fillna(0)
    customers_with_rfm['Monetary'] = customers_with_rfm['Monetary'].fillna(0)

    # Select features for clustering
    features = ['Recency', 'Frequency', 'Monetary']
    X = customers_with_rfm[features]

    # Scale the features
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    # Apply K-means
    kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
    customers_with_rfm['segment'] = kmeans.fit_predict(X_scaled)

    # Calculate average RFM for each segment for insight
    segment_rfm_means = customers_with_rfm.groupby('segment')[features].mean().round(2)

    # Get customer names/IDs for each segment
    customers_in_segments = {}
    for segment_id in sorted(customers_with_rfm['segment'].unique()):
        # Try to get 'name' column, if not available, fall back to 'customerid'
        customer_identifiers = customers_with_rfm[customers_with_rfm['segment'] == segment_id]
        if 'name' in customer_identifiers.columns and not customer_identifiers['name'].isnull().all():
            customers_in_segments[segment_id] = customer_identifiers['name'].tolist()
        else:
            customers_in_segments[segment_id] = customer_identifiers['customerid'].tolist()


    return customers_with_rfm, segment_rfm_means, customers_in_segments # Return all three


def analyze_campaigns(campaigns_df, sales_df):
    results = []
    for _, row in campaigns_df.iterrows():
        start_date = pd.to_datetime(row['start_date'])
        end_date = pd.to_datetime(row['end_date'])
        brand_id = row.get('target_brand')
        offer_type = row.get('offer_type', 'N/A')
        campaign_name = row.get('campaign_name', f"Campaign {row['campaign_id']}")

        pre_sales = sales_df[(pd.to_datetime(sales_df['date']) < start_date)]
        post_sales = sales_df[(pd.to_datetime(sales_df['date']) >= start_date) & (pd.to_datetime(sales_df['date']) <= end_date)]

        if brand_id:
            pre_sales = pre_sales[pre_sales['brandid'] == brand_id]
            post_sales = post_sales[post_sales['brandid'] == brand_id]

        pre_payout = pre_payout = pre_sales['payout'].sum()
        post_payout = post_sales['payout'].sum()

        results.append({
            "campaign_id": row['campaign_id'],
            "campaign_name": campaign_name,
            "budget": row['budget'],
            "start_date": start_date.strftime('%Y-%m-%d'),
            "end_date": end_date.strftime('%Y-%m-%d'),
            "target_brand": brand_id if brand_id else "All Brands",
            "offer_type": offer_type,
            "pre_payout": pre_payout,
            "post_payout": post_payout,
            "profit": post_payout - row['budget']
        })

    return pd.DataFrame(results)

def build_prompt(campaign_df, analysis_df, customers_df, segment_rfm_means, customers_in_segments, user_target_segment=None, user_desired_brand=None):
    prompt = """أنت مدير تسويق ذكي ومحلل بيانات متمرس. بناءً على بيانات الحملات التاريخية واتجاهات المبيعات وتحليل سلوك العملاء المجمع (K-Means)، قدم توصيات تسويقية مخصصة للغاية للمستخدم لزيادة المبيعات والأرباح. يجب أن تكون توصياتك مفصلة، قابلة للتنفيذ، ومدعومة بالبيانات.
    جميع قيم "المكافأة" (payout) و"الميزانية" (budget) و"الربح" (profit) هي بالجنيه المصري (EGP).
    """

    # Get the current date to help LLM suggest future dates
    current_date = datetime.now().strftime('%Y-%m-%d')
    prompt += f"\n**التاريخ الحالي:** {current_date}\n"

    if user_target_segment is not None or user_desired_brand:
        prompt += "\n**مدخلات المستخدم المحددة:**\n"
        if user_target_segment is not None:
            prompt += f"- شريحة العملاء المستهدفة: {user_target_segment} (بناءً على تجميع K-Means لسلوك الشراء)\n"
        if user_desired_brand:
            prompt += f"- العلامة التجارية المستهدفة: {user_desired_brand}\n"
        prompt += "\nبناءً على هذه المدخلات، عليك اقتراح تفاصيل الحملة التالية: عرضًا محددًا، تاريخ بدء مقترحًا، ومجموعة مستهدفة دقيقة (شريحة العملاء)، أو حتى علامة تجارية معينة إذا كانت ذات صلة. ركز على الحملات التي أدت إلى زيادة الأرباح بشكل كبير في الماضي، مع الأخذ في الاعتبار خصائص شريحة العملاء المستهدفة.\n"
    else:
        prompt += "\nقم بتحليل أداء الحملات السابقة وخصائص شرائح العملاء المستندة إلى سلوك الشراء (K-Means). عليك اقتراح أفضل تفاصيل الحملة لزيادة الأرباح بشكل عام، مع الأخذ في الاعتبار شرائح العملاء الأكثر ربحية أو التي لديها إمكانات نمو عالية. يجب أن تكون التوصيات محددة جدًا وتستند إلى البيانات.\n"

    prompt += f"\n**أداء الحملات السابقة (الربح هو الفرق بين المبيعات بعد الحملة والميزانية، بالجنيه المصري EGP):**\n"
    prompt += f"{analysis_df.to_string(index=False)}\n"

    prompt += f"\n**تحليل شرائح العملاء (تجميع K-Means بناءً على سلوك الشراء - Recency, Frequency, Monetary):**\n"
    prompt += f"هذه هي متوسطات قيم Recency (عدد الأيام منذ آخر شراء)، Frequency (عدد المشتريات)، و Monetary (إجمالي الإنفاق) لكل شريحة عملاء. القيم النقدية هي بالجنيه المصري (EGP):\n"
    prompt += f"{segment_rfm_means.to_string()}\n"
    prompt += f"\nتفسير تقريبي للشرائح (بناءً على القيم أعلاه):\n"
    prompt += f"- **الشرائح ذات Recency المنخفضة (أيام قليلة)** و Frequency/Monetary العالية: عملاء نشطون ومخلصون (VIPs, Loyal).\n"
    prompt += f"- **الشرائح ذات Recency العالية (أيام كثيرة)** و Frequency/Monetary المنخفضة: عملاء معرضون لخطر التوقف أو غير نشطين (Churning, Inactive).\n"
    prompt += f"- **الشرائح ذات Recency المنخفضة و Frequency/Monetary المنخفضة:** عملاء جدد أو منخفضي القيمة (New, Low Value).\n"
    prompt += f"- **الشرائح المتوسطة:** عملاء منتظمون (Regular).\n"
    prompt += f"\n**يجب عليك استخدام هذه التفسيرات الأولية لفهم سلوك كل شريحة وتوجيه توصياتك.**\n"

    prompt += f"\n**العملاء في كل شريحة (للمراسلة المباشرة أو الاستهداف):**\n"
    for segment_id, customers_list in customers_in_segments.items():
        # Limit the number of customers listed to avoid excessively long prompts
        display_customers = customers_list[:5] # Display first 5 customers
        if len(customers_list) > 5:
            prompt += f"- الشريحة {segment_id} ({len(customers_list)} عميل): {', '.join(map(str, display_customers))} وآخرون...\n"
        else:
            prompt += f"- الشريحة {segment_id} ({len(customers_list)} عميل): {', '.join(map(str, display_customers))}\n"
    prompt += "\n"

    prompt += f"\n**الحملات المتاحة سابقًا (للمرجع):**\n"
    prompt += f"{campaign_df[['campaign_id', 'start_date', 'end_date', 'budget', 'target_brand']].to_string(index=False)}\n"

    prompt += f"\n**التوصيات المطلوبة:**\n"
    prompt += f"1.  **تحليل الشريحة المستهدفة:** إذا تم تحديد شريحة مستهدفة من قبل المستخدم، قم بوصف خصائص هذه الشريحة بناءً على قيم RFM الخاصة بها. إذا لم يتم تحديد شريحة، حدد الشريحة (أو الشرائح) التي تعتقد أنها ستستجيب بشكل أفضل لحملة جديدة لتحقيق أقصى ربح، واشرح لماذا. اذكر أسماء بعض العملاء البارزين في هذه الشريحة كمثال.\n"
    prompt += f"2.  **تفاصيل الحملة التالية:** بناءً على أداء الحملات السابقة وخصائص الشريحة المستهدفة، اقترح ما يلي:\n"
    prompt += f"    * **عنوان الحملة المقترح:** (مثال: حملة ولاء العملاء VIP، عرض خاص للعملاء الجدد، تنشيط العملاء غير النشطين).\n"
    prompt += f"    * **تاريخ البدء المقترح:** (مثال: 'YYYY-MM-DD'). يفضل تاريخ في المستقبل القريب. **اشرح بوضوح لماذا تم اختيار هذا التاريخ (على سبيل المثال: يتوافق مع أنجح فترات الحملات السابقة، يستهدف العملاء النشطين قبل موسم الأعياد، يركز على إعادة تنشيط العملاء غير النشطين بعد فترة هدوء).**\n"
    prompt += f"    * **المدة المقترحة:** (مثال: أسبوعين، شهر).\n"
    prompt += f"    * **العرض/الخصم المقترح:** (مثال: خصم 20% على منتجات العلامة التجارية X، شحن مجاني، نقاط ولاء مضاعفة، هدية عند الشراء).\n"
    prompt += f"    * **المنتجات/الخدمات المستهدفة:** (مثال: فئة معينة من المنتجات، علامة تجارية محددة).\n"
    prompt += f"    * **المجموعة المستهدفة الدقيقة:** (اذكر رقم الشريحة أو الشرائح المحددة، وصف موجز لسبب استهدافهم).\n"
    prompt += f"    * **الميزانية المقترحة:** (بالجنيه المصري EGP، بناءً على أداء الحملات السابقة الناجحة).\n"
    prompt += f"3.  **السبب المنطقي والتوقع:** اشرح بوضوح لماذا هذه التوصيات هي الأفضل بناءً على البيانات المقدمة، وتوقع الزيادة المحتملة في المبيعات والأرباح الناتجة عن تطبيق هذه الحملة. كن محددًا في أرقام الربح المتوقعة بالجنيه المصري (EGP) إن أمكن.\n"
    prompt += f"\n**اللغة المطلوبة:** يجب أن تكون إجابتك باللغة العربية الفصحى. لا تقدم أبدًا توصيات عامة أو غير قابلة للتنفيذ.\n"
    prompt += f"\n**ملاحظة هامة:** إذا كانت الحملات السابقة لا تحتوي على تفاصيل كافية (مثل offer_type)، فاستخدم أفضل تخمين لديك أو قم بتضمين عبارة 'تفاصيل العرض غير متوفرة في البيانات التاريخية، لكنني أوصي بـ...'.\n"

    return prompt

def recommend(user_target_segment=None, user_desired_brand=None):
    data = fetch_data()
    customers_df, segment_rfm_means, customers_in_segments = segment_customers(data['customers'], data['sales'])
    analysis_df = analyze_campaigns(data['campaigns'], data['sales'])

    prompt = build_prompt(data['campaigns'], analysis_df, customers_df, segment_rfm_means, customers_in_segments,
                          user_target_segment=user_target_segment,
                          user_desired_brand=user_desired_brand)

    llm = ChatGoogleGenerativeAI(
        model="gemini-1.5-flash",
        temperature=0.7,
        google_api_key=gemini_api_key,
    )
    response = llm.predict(prompt)

    # The key change here: return the raw response string from the LLM
    return response
