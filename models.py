
from pydantic import BaseModel
from typing import List
import datetime
from typing import List, Optional# === Models ===

class AdvisorRequest(BaseModel):
    user_desired_brand: Optional[str] = None # Allow None or empty string for no selection
    
class ChurnUser(BaseModel):
    name: str # User_id removed, name is now the primary identifier
    churn_probability: float
    cause: Optional[str] = None
    seen: bool = False # New field to track if the alert has been seen

class ChurnNotificationPayload(BaseModel):
    timestamp: str # ISO formatted string
    churn_users: List[ChurnUser]
    message: Optional[str] = None

class ChurnAlertResponse(BaseModel):
    timestamp: str
    churn_users: List[ChurnUser]
    message: Optional[str] = None
# Define request model
class ChatRequest(BaseModel):
    user_message: str