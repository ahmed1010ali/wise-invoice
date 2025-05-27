from HelperFunctions.Libraries import *



# Configure marker
config = {
    "output_format": "html",
    "disable_links": "true",
    "disable_image_extraction": "true",
    "use_llm":"true",
    "gemini_api_key":gemini_api_key,

}
config_parser = ConfigParser(config)

# Create converter
converter = TableConverter(
    config=config_parser.generate_config_dict(),
    artifact_dict=create_model_dict(),
    renderer=config_parser.get_renderer(),
)

def clean_html_to_text(html):
    soup = BeautifulSoup(html, 'lxml')
    return soup.get_text(separator=' ').replace('\n', ' ').strip()
def extract_with_llm(html):
    text = clean_html_to_text(html)

    prompt = ("أوجد التاريخ، اسم المنطقة، وجدول القيم من هذا النص HTML المُحول إلى نص:\n\n"
        f"{text}\n\n"
        "أعطني النتيجة بصيغة JSON تحتوي على: التاريخ، المنطقة، وقائمة من القيم مثل:\n"
        "[[رقم المندوب, المبلغ, الخط, رقم الحساب, اسم العميل], ...]\n"
        " ملاحظة: اذا لم تجد اسم منطقة اعتبر القيمة الافتراضية لها هي القاهرة واذا لم تجد التاريخ اعتبر القيمة الافتراضية تاريخ اليوم  "
        )
    response = llm.call(prompt)
    
    # Clean response from markdown formatting or extra backticks
    cleaned_response = response.strip().strip('`')
    if cleaned_response.startswith("json"):
        cleaned_response = cleaned_response[4:].strip()
    if cleaned_response.startswith("{") is False:
        print("Raw LLM output:", repr(cleaned_response))  # Debug print

    try:
        data_dict = json.loads(cleaned_response)
    except json.JSONDecodeError as e:
        print("Error parsing JSON:", e)
        data_dict = {}

    return data_dict

