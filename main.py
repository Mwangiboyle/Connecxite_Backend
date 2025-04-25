from fastapi import FastAPI, Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from supabase import create_client, Client
from pydantic import BaseModel
from urllib.parse import urlparse
from typing import List, Optional
import config
import jwt
import uuid
import os
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="Connecxite backend. made with FastAPI")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://linkedin-connection-enhancer-2.onrender.com", "http://localhost:4000","http://localhost:8000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize Supabase client
supabase_url = os.getenv("SUPABASE_URL", "https://dusdlcrkvethipcqwnzk.supabase.co")
supabase_key = os.getenv("SUPABASE_KEY", "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImR1c2RsY3JrdmV0aGlwY3F3bnprIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDExNzUzMDEsImV4cCI6MjA1Njc1MTMwMX0.o7mTueOtmmVckk-KlyKQc5GhpvHGez4El-evQtil62s")
supabase: Client = create_client(supabase_url, supabase_key)

SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "django-insecure-ja(+nqnk)q6y=)3)fq^6s39)1a#d^r&&q7o19&p=yu8f@*d7w&")
security = HTTPBearer()
ALGORITHM = "HS256"

class User(BaseModel):
    email: str
    password: str

class LinkedInRequest(BaseModel):
    user_url: str
    target_url: str
    intent: str = "network"
    character_length: int = 300
    attributes: Optional[List[str]] = None

class ConnectionStatusUpdate(BaseModel):
    request_id: int
    new_status: str

class Data(BaseModel):
    user_url: str
    target_url: str
    intent: str = "network"

def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")

def extract_username(linkedin_url: str):
    return urlparse(linkedin_url).path.strip("/").split("/")[-1]

@app.post("/generate-message")
async def generate_message(request: LinkedInRequest, payload: dict = Depends(verify_token)):
    try:
        user_profile = config.get_profile_data(request.user_url)
        target_profile = config.get_profile_data(request.target_url)

        message = config.generate_ai_message(
            user_data=user_profile,
            target_data=target_profile,
            intent=request.intent,
            attributes=request.attributes,
            character_length=request.character_length
        )

        #await record_connection_request(request, payload)
        return {"message": message}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/record-connection-request")
async def record_connection_request(request: LinkedInRequest, payload: dict = Depends(verify_token)):
    try:
        user_id = payload.get("user_id")
        # Convert Django user ID to UUID string format
        user_uuid = str(uuid.UUID(int=int(user_id)))
        industry = config.extract_industry(request.target_url)
        target_url = request.target_url  # Store the full URL instead of just username

        data = supabase.table("connection_requests").insert({
            "user_id": user_uuid,
            "target_url": target_url,  # Changed from target_username to target_url
            "template_used": request.intent,
            "industry": industry,
            "status": "sent"
        }).execute()

        # Ensure user_metrics table has this user
        supabase.table("user_metrics").upsert({
            "user_id": user_uuid,
            "total_requests": 1
        }, on_conflict="user_id").execute()

        return {"message": "Request recorded", "request_id": data.data[0]['id']}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/update-connection-status")
async def update_connection_status(update: ConnectionStatusUpdate, payload: dict = Depends(verify_token)):
    try:
        user_id = payload.get("user_id")
        user_uuid = str(uuid.UUID(int=int(user_id)))
        
        supabase.table("connection_requests").update({
            "status": update.new_status
        }).eq("id", update.request_id).execute()

        # Recalculate metrics
        supabase.rpc("calculate_user_metrics", {"user_id": user_uuid}).execute()
        
        return {"message": "Status updated"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/get-metrics")
async def get_metrics(payload: dict = Depends(verify_token)):
    try:
        user_id = payload.get("user_id")
        user_uuid = str(uuid.UUID(int=int(user_id)))

        # Get metrics data
        metrics = supabase.table("user_metrics").select("*").eq("user_id", user_uuid).execute()
        industry_metrics = supabase.table("industry_metrics").select("*").eq("user_id", user_uuid).execute()
        template_metrics = supabase.table("template_metrics").select("*").eq("user_id", user_uuid).execute()

        # Handle case where metrics don't exist yet
        if not metrics.data:
            return {
                "connection_requests": 0,
                "acceptance_rate": 0,
                "active_conversations": 0,
                "response_rate": 0,
                "industries": {},
                "templates": {}
            }

        return {
            "connection_requests": metrics.data[0].get("total_requests", 0),
            "acceptance_rate": metrics.data[0].get("acceptance_rate", 0),
            "active_conversations": metrics.data[0].get("active_conversations", 0),
            "response_rate": metrics.data[0].get("response_rate", 0),
            "industries": {im["industry"]: im["success_rate"] for im in industry_metrics.data},
            "templates": {tm["template_name"]: tm["success_rate"] for tm in template_metrics.data}
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
@app.post("/generate-voice-script")
async def generate_voice_script(request: Data):
    try:
        user_data  =config.get_profile_data(request.user_url)
        target_data = config.get_profile_data(request.target_url)
        response = config.generate_voice_script(user_data,target_data,request.intent)
        return {"message": response}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
        
@app.get("/")
async def root():
    return {"message": "Welcome to the FastAPI Connecxite backend"}