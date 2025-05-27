import io
import cv2
import tempfile
import datetime
import traceback
import numpy as np
from fastapi.middleware.cors import CORSMiddleware
from pdf2image import convert_from_bytes, convert_from_path
from PIL import Image
from typing import Optional 
from pydantic import BaseModel
from models import *
from fastapi import FastAPI, Request
from HelperFunctions.Chatbot import *
from fastapi.staticfiles import StaticFiles
#from HelperFunctions.CustomerChurn import *
from HelperFunctions.MarktingAdvisor import *
from fastapi.templating import Jinja2Templates
from HelperFunctions.InsertDataFunctions import *
from HelperFunctions.HandleInputFunctions import *
from HelperFunctions.ExtractTextFunctions import *
from fastapi import FastAPI, File, UploadFile, HTTPException
from apscheduler.schedulers.background import BackgroundScheduler
from fastapi.responses import FileResponse, JSONResponse, HTMLResponse, PlainTextResponse

app = FastAPI()
UPLOAD_FOLDER = "uploads"  
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# Paths
REPORT_PATH = "E:\pythoncodes\BillWise\HelperFunctions\Reports\sales_report.pdf"
DOWNLOAD_LINK = "/download-report"


@app.get("/")
async def render_index(request: Request):
    return templates.TemplateResponse("website.html", {"request": request}) 

@app.post("/predict", response_class=PlainTextResponse)
async def predict(file: UploadFile = File(...)):
    filename = file.filename.lower()
    file_content = await file.read()
    pdf_data = process_file_and_get_pdf(filename, file_content)
    path="uploads"
    with open(f"{path}/{filename}_processed.pdf","wb") as outputfile:
        outputfile.write(pdf_data)
    processed_pdf_path = os.path.join(path, f"{filename}_processed.pdf")
    rendered_data = converter(processed_pdf_path)
    extracted_data = extract_with_llm(rendered_data.html)
    try:
        insert_data(extracted_data)
        return "لقد تم التسجيل في قاعدة البيانات بنجاح"
    except Exception as e:
        print(f"Database Insertion Error: {e}")
        return "لقد حدث خطأ أثناء التسجيل في قاعدة البيانات! يرجي المحاولة مرةأخري"
        
@app.get("/download-report")
async def download_report():
    return FileResponse(
        REPORT_PATH,
        media_type='application/pdf',
        filename='sales_report.pdf'
    )

# Chat endpoint
@app.post("/chat")
async def chat_with_agent(query: ChatRequest):
    user_input = query.user_message.strip()

    if user_input.lower() in ["exit", "quit", "خروج"]:
        return {"response": ": مع السلامة!", "status": "exit"}

    if not user_input:
        return {"response": "من فضلك أدخل استفسار.", "status": "empty"}

    try:
        prompt = f"""
        أنت وكيل مسؤول عن تصنيف نية المستخدم.
        report فالإجابة هي PDF إذا كان المستخدم يسأل عن إنشاء تقرير أو ملف.
        chat اذا كان سؤالاً عاديا فالاجابة هي.
        report او كلمة chat  لا تضف اي شرح اخر فقط الاجابة كلمة.
        سؤال المستخدم هو {user_input}
        """
        intent_response = llm.call(prompt).strip()

        if intent_response == "report":
            agent_response = Report_Agent.run(user_input)
            # Make sure this return matches the structure the JS expects
            return JSONResponse(content={"response": "تم إنشاء التقرير اضغط هنا للتنزيل", "download_url": DOWNLOAD_LINK}) # Modified
        else:
            agent_response = General_agent.run(user_input)
            return {"response": agent_response}

    except Exception as e:
        return {"response": f"حدث خطأ: {str(e)}"}
    



@app.post("/ask_advisor", response_class=JSONResponse)
async def ask_advisor_endpoint(request: AdvisorRequest):
    """
    Endpoint to trigger the recommendation process and return the results as a plain text string.
    """
    try:
        user_desired_brand = request.user_desired_brand if request.user_desired_brand else None

        # Call your recommend function, which now returns a formatted string
        # Pass the user_desired_brand to the recommend function
        recommendations_text: str = recommend(user_desired_brand=user_desired_brand)

        # Return the formatted string directly as a JSON object with a single key
        return JSONResponse(content={'recommendations': recommendations_text})

    except Exception as e:
        # Return error as JSON
        print(f"Error in ask_advisor_endpoint: {e}") # Log the error for debugging
        return JSONResponse(content={'error': f'An internal server error occurred: {str(e)}'}, status_code=500)

# ENDPOINT TO GET BRANDS FROM SUPABASE
@app.get("/get_brands", response_class=JSONResponse)
async def get_brands():
    """
    Fetches all unique brand names from the 'invoices' table in Supabase.
    """
    try:
        # Query Supabase to get all unique brand names from your 'invoices' table
        # Replace 'invoices' with your actual table name if different
        # Replace 'brand_column_name' with the actual column name that stores brands
        response = supabase.from_('brands').select('name').execute()

        # Check if there's data and extract unique brand names
        if response.data:
            # Extract brands, filter out None/empty strings, and convert to a set for uniqueness, then back to a list
            brands = sorted(list(set([
                item['name'] for item in response.data
                if item['name'] is not None and item['name'].strip() != ''
            ])))
            return JSONResponse(content={"brands": brands})
        else:
            return JSONResponse(content={"brands": []})

    except Exception as e:
        print(f"Error fetching brands from Supabase: {e}")
        return JSONResponse(content={'error': f'Could not fetch brands: {str(e)}'}, status_code=500)



CHURN_ALERTS_DB: List[ChurnUser] = []

# === Dummy churn detection ===
def get_churned_list():
    return [
        {"name": "Ahmed", "churn_probability": 0.9, "cause": "No recent purchases"},
        {"name": "Sara", "churn_probability": 0.6, "cause": "High return rate"},
        {"name": "Fatima", "churn_probability": 0.85, "cause": "Decreased engagement"},
    ]

# === Churn Notification Logic ===
def send_monthly_churn_notification():
    new_churn_users = [ChurnUser(**user_data, seen=False) for user_data in get_churned_list()]
    CHURN_ALERTS_DB.extend(new_churn_users) # Add new churn users to the global list
    print(f"[{datetime.now().isoformat()}] Monthly churn notification sent. Added {len(new_churn_users)} new alerts.")

@app.post("/churn-notifications", response_model=ChurnAlertResponse, status_code=201)
async def receive_churn_notifications(payload: ChurnNotificationPayload):
    print(f"Received churn notification via POST at {datetime.datetime.now()}: {payload.dict()}")
    processed_users = [ChurnUser(**user.dict(), seen=False) for user in payload.churn_users]
    CHURN_ALERTS_DB.extend(processed_users)
    return JSONResponse(content={
        "timestamp": datetime.datetime.now().isoformat(),
        "churn_users": processed_users,
        "message": "Churn notification received and processed successfully."
    }, status_code=201)

@app.get("/get-churn-alerts", response_model=List[ChurnUser])
async def get_churn_alerts():
    return list(CHURN_ALERTS_DB)

@app.post("/mark-churn-alert-as-seen/{name}") # Changed path to use name
async def mark_churn_alert_as_seen(name: str):
    found_any = False
    for alert in CHURN_ALERTS_DB:
        if alert.name == name:
            alert.seen = True
            found_any = True
            print(f"Marked alert for name {name} as seen.")
    
    if not found_any:
        raise HTTPException(status_code=404, detail=f"Alerts for name {name} not found.")
    
    return {"message": f"Alerts for name {name} marked as seen."}

# === Scheduler Setup ===
scheduler = BackgroundScheduler()

# Schedule job: every month on the 23rd at 10:00 AM
scheduler.add_job(send_monthly_churn_notification, 'cron', day=24, hour=12, minute=18)

scheduler.start()