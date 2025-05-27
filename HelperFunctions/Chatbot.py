from HelperFunctions.Libraries import *

DATABASE_SCHEMA = """
Database Schema:

Tables:
- customers(customerid, name)
- branches(branchid, name)
- customerbranches(customerid, branchid)
- brands(brandid, name)
- accounts(accountid,accountnumber,brandid,customerid)
- salespeople(salespersonid,name,code, branchid, brandid)
- sales(customerid,accountid,brandid,salespersonid,payout,date,branchid)

Relationships:
- customerid of table customers is foreign key to customerbrandss(customerid), accounts(customerid), sales(customerid)
- branchid of table branches is foreign key to customerbranches(branchid), sales(branchid), salespeople(branchid)
- brandid of table brands is foreign key to accounts(brandid), sales(brandid), salespeople(brandid)
- accountid of table accounts is foreign key to sales(accountid)
- salespersonid of table salespeople is foreign key to sales(salespersonid)
"""

General_agent_prompt = f"""
أنت مساعد ذكي تفهم الأسئلة باللهجة المصرية وتحوّلها إلى استعلامات
ثم تستخدم الادوات المرسلة لتنفيذ الاستعلامات وعرض البيانات الفعلية SQL تعمل على قاعدة بيانات PostgreSQL.

مخطط قاعدة البيانات:
{DATABASE_SCHEMA}

-- استخدم علامات اقتباس مفردة عند التعامل مع النصوص: مثل name = 'هالة'.
- إذا لم يكن السؤال واضحًا، اطلب من المستخدم توضيحًا.
- استند دائمًا إلى المخطط التالي الموجود في المحادثة.
- لا تفترض أو تخمّن البيانات.
- لا تنفذ استعلامات تعديل (INSERT, UPDATE, DELETE)، فقط SELECT.
- تأكد من كتابة صحيحة لاسترجاع البيانات postgreSQL syntax.
- اتبع قواعد PostgreSQL فقط — تجنب أي صيغة خاصة بـ MySQL أو SQL Server.

PostgreSQL SQL Style Guide:
- Use LIMIT instead of TOP
- Use ILIKE for case-insensitive text filtering
- Use NOW() or CURRENT_DATE for current timestamps
- Avoid square brackets [ ]; use double quotes for column names only when necessary, e.g. "column"
- Use COALESCE() instead of ISNULL()
- Use standard joins and PostgreSQL-compatible expressions
"""

Report_agent_prompt = f"""
أنت مساعد ذكي تفهم الأسئلة باللهجة المصرية وتحوّلها إلى استعلامات SQL تعمل على قاعدة بيانات PostgreSQL.

مخطط قاعدة البيانات:
{DATABASE_SCHEMA}

مهمتك الأساسية هي:
- إنشاء تقارير مبيعات لكل علامة تجارية حسب السنة التي يطلبها المستخدم.
- إنشاء تقارير مبيعات لكل علامة تجارية حسب جزء معين من السنة التي يطلبها المستخدم.(مهم: التقرير يجب أن يحتوي على إجمالي عدد المنتجات المباعة وإجمالي الإيرادات لكل علامة تجارية خلال السنة.)
- اذا طلب المستخدم تقرير عن جزء معين من السنة يجب الالتزام بهذا الجزء بدقة, مثال اذا طلب تقرير عن اول اربعة اشهر من السنة يجب الالتزام بهذه الشهور فقط
- لا تضع الاستعلام داخل كود من نوع sql, فقط أرسل الاستعلام كنص عادي.
-- استخدم علامات اقتباس مفردة عند التعامل مع النصوص: مثل name = 'هالة'.
- لا تنفذ استعلامات تعديل (INSERT, UPDATE, DELETE)، فقط SELECT.
- تأكد من كتابة صحيحة لاسترجاع البيانات postgreSQL syntax.
"""

General_agent_llm = ChatGoogleGenerativeAI(
    model="gemini-1.5-flash",
    temperature=0,
    #convert_system_message_to_human=True,
    google_api_key=gemini_api_key,
    system_message=General_agent_prompt
)

Report_agent_llm = ChatGoogleGenerativeAI(
    model="gemini-1.5-flash",
    temperature=0,
    google_api_key=gemini_api_key,
    system_message=Report_agent_prompt
)

# SET PDF DOWNLOAD PATH
# path="Report"
# PDF_PATH = os.path.join(path, "report.pdf")
 
PDF_PATH = 'E:\pythoncodes\BillWise\HelperFunctions\Reports\sales_report.pdf'


def reshape_arabic_text(text):
    reshaped = arabic_reshaper.reshape(text)
    bidi_text = get_display(reshaped)
    return bidi_text
            
@tool
def run_supabase_general_sql_tool(query: str) -> str:
    """
    Executes a SELECT SQL query on the Supabase PostgreSQL database.
    Only supports SELECT statements. Returns the result as a string.
    """
    try:
        query = query.strip().rstrip(";")
        result = supabase.rpc("execute_sql", {"sql": query}).execute()
        if result.data:
            return str(result.data)
        else:
            return "لا توجد نتائج."
    except Exception as e:
        return f"حدث خطأ أثناء تنفيذ الاستعلام: {str(e)}"
    
#helper
def clean_sql_query(raw: str) -> str:
    # Remove leading/trailing spaces and newlines
    raw = raw.strip()

    # Remove opening triple backtick with optional 'sql'
    raw = re.sub(r"^```(?:sql)?\s*", "", raw)

    # Remove closing triple backtick
    raw = re.sub(r"\s*```$", "", raw)

    return raw.strip().rstrip(";")

@tool
def run_supabase_report_sql_tool(query: str) -> str:
    """
    Executes a SELECT SQL query on the Supabase PostgreSQL database.
    Only supports SELECT statements. Returns the result as a string.
    """
    try:
        # Remove any sql ...  or ... code fences
        query=clean_sql_query(query)
        result = supabase.rpc("execute_sql", {"sql": query}).execute()
        if result.data:
             # Convert result to DataFrame
            df = pd.DataFrame(result.data)
    
            # Generate PDF
            # === Register Arabic font ===

            pdfmetrics.registerFont(TTFont('Amiri','E:\pythoncodes\BillWise\Fonts\Amiri-Regular.ttf'))  # Use correct path to .ttf file
            registerFontFamily('Amiri', normal='Amiri')
            # === Generate PDF ===
            doc = SimpleDocTemplate(PDF_PATH, pagesize=A4)
            styles = getSampleStyleSheet()
            # Customize styles for Arabic
            styles['Title'].fontName = 'Amiri'
            styles['Title'].alignment = 2  # Right-align
            
            arabic_style = styles["BodyText"]
            arabic_style.fontName = 'Amiri'
            arabic_style.alignment = 2  # Right-align
            elements = []
            # Create custom centered Arabic title style
            centered_title_style = styles['Title'].clone('CenteredTitle')
            centered_title_style.fontName = 'Amiri'
            centered_title_style.alignment = TA_CENTER  # Center alignment
            # Reshape the Arabic title
            reshaped_title = get_display(arabic_reshaper.reshape(" تقرير المبيعات"))
            
            # Add the centered title
            elements.append(Paragraph(reshaped_title, centered_title_style))
            elements.append(Spacer(1, 12))
            # Prepare data
            
            # Prepare reshaped data
            reshaped_data = []
            # Reorder columns: move 'brand_name' to the end
            df = df[['total_sales', 'brand_name']]  # Adjust this list based on your actual column names

            # Reshape column headers
            # Replace column names with Arabic equivalents
            column_mapping = {
                'brand_name': 'خطوط الشركة',
                'total_sales': 'إجمالي المبيعات'
            }
            df.rename(columns=column_mapping, inplace=True)
            # Reshape new Arabic column headers
            reshaped_headers = [reshape_arabic_text(col) for col in df.columns]
            reshaped_data.append(reshaped_headers)
            
            # Reshape each row
            for row in df.values:
                reshaped_row = [reshape_arabic_text(str(cell)) if isinstance(cell, str) else cell for cell in row]
                reshaped_data.append(reshaped_row)
            # Sum total sales
            total_sales_sum = df['إجمالي المبيعات'].sum()
            
            # Create summary row (اجمالي مبيعات الشركة)
            summary_row = [total_sales_sum, reshape_arabic_text("إجمالي مبيعات الشركة")]
            
            # Append the summary row at the end
            reshaped_data.append(summary_row)

            data = reshaped_data
                        
            table = Table(data)
            table.setStyle(TableStyle([
                ('FONTNAME', (0, 0), (-1, -1), 'Amiri'),
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'RIGHT'),
                ('GRID', (0, 0), (-1, -1), 1, colors.black)
            ]))
            elements.append(table)
            doc.build(elements)

            return f"تم إنشاء التقرير بنجاح "
        else:
            return "لا توجد نتائج."
       
    except Exception as e:
        return f"حدث خطأ أثناء تنفيذ الاستعلام: {str(e)}"
    

General_agent_tools = [run_supabase_general_sql_tool]

Report_agent_tools = [
    Tool(
        name="run_supabase_report_sql_tool",
        func=run_supabase_report_sql_tool,
        description=(
            "ينفذ استعلامات SELECT على قاعدة بيانات PostgreSQL، "
            " مثل تقارير المبيعات لكل علامة تجارية خلال سنة معينة او خلال فترة محددة من السنة"
        )
    )
]

memory = ConversationBufferMemory(memory_key="chat_history", return_messages=True)
memory.chat_memory.add_user_message("ما هو مخطط قاعدة البيانات؟")
memory.chat_memory.add_ai_message(f"مخطط قاعدة البيانات:\n{DATABASE_SCHEMA}")

General_agent = initialize_agent(
    tools=General_agent_tools,
    llm=General_agent_llm,
    agent=AgentType.CONVERSATIONAL_REACT_DESCRIPTION,
    memory=memory,
    verbose=True,
)

Report_Agent = initialize_agent(
    tools=Report_agent_tools,
    llm=Report_agent_llm,
    agent=AgentType.CONVERSATIONAL_REACT_DESCRIPTION,
    memory=memory,
    verbose=True,
)