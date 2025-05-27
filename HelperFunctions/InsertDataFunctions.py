from HelperFunctions.Libraries import *

def get_customer_names():
    response = supabase.table("customers").select("name").execute()
    if response.data:
        return [item["name"] for item in response.data]  
    else:
        print("No data returned.")
        return []

def get_brand_name():
    response = supabase.table("brands").select("name").execute()
    if response.data:
        return [item["name"] for item in response.data]  
    else:
        print("No data returned.")
        return []
def fuzzy_check(value, reference_list, threshold=50):
    match, score, _ = process.extractOne(value, reference_list, scorer=fuzz.ratio)
    if score >= threshold:
        return match
    return None
    
def validate(skipped_row,customer_names,brand_names):
    matched_client = fuzzy_check(skipped_row[4], customer_names)
    matched_brand = fuzzy_check(skipped_row[2], brand_names)
    skipped_row[4] = matched_client
    skipped_row[2] = matched_brand
    
    return skipped_row

def insert_sales_records(data):
    skipped_rows = []
    date_str = data["التاريخ"]
    date = datetime.strptime(date_str, "%d/%m/%Y").date()
    branch_name = data["المنطقة"]
    records = data["القيم"]
    for record in records:
        code, payout, brand_name, account_number, customer_name = record

        if code is None:
            continue

        # Get foreign keys
        customer = supabase.table("customers").select("customerid").eq("name", customer_name).execute()
        account = supabase.table("accounts").select("accountid").eq("accountnumber", account_number).execute()
        brand = supabase.table("brands").select("brandid").eq("name", brand_name).execute()
        salesperson = supabase.table("salespeople").select("salespersonid").eq("code", code).execute()
        branch = supabase.table("branches").select("branchid").eq("name", branch_name).execute()

        if not (customer.data and account.data and brand.data and salesperson.data and branch.data):
            skipped_rows.append(record)
            print(f"Skipping record due to missing FK: {record}")
            continue

        # Insert sales row
        sales_row = {
            "customerid": customer.data[0]["customerid"],
            "accountid": account.data[0]["accountid"],
            "brandid": brand.data[0]["brandid"],
            "salespersonid": salesperson.data[0]["salespersonid"],
            "branchid": branch.data[0]["branchid"],
            "date": str(date),
            "payout": payout
        }
        supabase.table("sales").insert(sales_row).execute()
        print(f"Inserted: {sales_row}")

    return {
        "التاريخ": date_str,
        "المنطقة": branch_name,
        "القيم": skipped_rows
    }

def insert_data(data):
    skipped_rows = insert_sales_records(data)
    validated_rows = []
    if skipped_rows["القيم"]:
        customer_names = get_customer_names()
        brand_names = get_brand_name()
        for i in range(len(skipped_rows["القيم"])):
            skipped_rows["القيم"][i] = validate(skipped_rows["القيم"][i], customer_names, brand_names)
        print("------------------------------------------------------------------------------------------------------------------------------------")
        print("Insert Skipped Rows:")
        insert_sales_records(skipped_rows)