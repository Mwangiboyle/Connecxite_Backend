from fastapi import FastAPI, Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from supabase import create_client, Client
from pydantic import BaseModel
from urllib.parse import urlparse
from typing import List, Optional
import config
import jwt
import os
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="Connecxite backend. made with FastAPI")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://linkedin-connection-enhancer-2.onrender.com", "http://localhost:4000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

supabase_url = os.getenv("SUPABASE_URL")
supabase_key = os.getenv("SUPABASE_KEY")
supabase: Client = create_client(supabase_url, supabase_key)

security = HTTPBearer()
SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "your-fallback-secret")
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

        await record_connection_request(request, payload)
        return {"message": message}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/record-connection-request")
async def record_connection_request(request: LinkedInRequest, payload: dict = Depends(verify_token)):
    try:
        user_id = payload.get("user_id")
        industry = config.extract_industry(request.target_url)

        data = supabase.table("connection_requests").insert({
            "user_id": user_id,
            "target_url": request.target_url,
            "template_used": request.intent,
            "industry": industry,
            "status": "sent"
        }).execute()

        supabase.rpc("increment_total_requests", {"user_id": user_id}).execute()
        return {"message": "Request recorded", "request_id": data.data[0]['id']}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/update-connection-status")
async def update_connection_status(update: ConnectionStatusUpdate, payload: dict = Depends(verify_token)):
    try:
        user_id = payload.get("user_id")
        supabase.table("connection_requests").update({
            "status": update.new_status
        }).eq("id", update.request_id).execute()

        config.calculate_user_metrics(user_id)
        return {"message": "Status updated"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/get-metrics")
async def get_metrics(payload: dict = Depends(verify_token)):
    try:
        user_id = payload.get("user_id")
        metrics = supabase.table("user_metrics").select("*").eq("user_id", user_id).execute().data[0]
        industry_metrics = supabase.table("industry_metrics").select("*").eq("user_id", user_id).execute().data
        template_metrics = supabase.table("template_metrics").select("*").eq("user_id", user_id).execute().data

        return {
            "connection_requests": metrics["total_requests"],
            "acceptance_rate": metrics["acceptance_rate"],
            "active_conversations": metrics["active_conversations"],
            "response_rate": metrics["response_rate"],
            "industries": {im["industry"]: im["success_rate"] for im in industry_metrics},
            "templates": {tm["template_name"]: tm["success_rate"] for tm in template_metrics}
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/")
async def root():
    return {"message": "Welcome to the FastAPI Connecxite backend"}
