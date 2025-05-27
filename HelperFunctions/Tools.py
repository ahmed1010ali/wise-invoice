from supabase import create_client, Client
from dotenv import load_dotenv
import os
from crewai.llm import LLM

load_dotenv()

# Access the variables
gemini_api_key= os.getenv("gemini_api_key")
SUPABASE_URL = os.getenv("DB_URL")
SUPABASE_KEY = os.getenv("DB_API")

#Define Tools
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

llm = LLM(model="gemini/gemini-1.5-flash", api_key=gemini_api_key,max_tokens=3000)

