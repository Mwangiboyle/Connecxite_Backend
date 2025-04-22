from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from supabase import create_client, Client
from datetime import datetime, timedelta
from pydantic import BaseModel
from urllib.parse import urlparse
from typing import List, Optional
import config
import os
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="Connecxite backend. made with fastapi")


app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://linkedin-connection-enhancer-2.onrender.com/", "http://localhost:4000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize Supabase client
supabase_url = os.getenv("SUPABASE_URL")
supabase_key = os.getenv("SUPABASE_KEY")
supabase: Client = create_client(supabase_url, supabase_key)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

class User(BaseModel):
    email: str
    password: str

class ConnectionStatusUpdate(BaseModel):
    request_id: int
    new_status: str  
    
class GoogleAuth(BaseModel):
    token: str
    
class LinkedInRequest(BaseModel):
    user_url: str
    target_url: str
    intent: str = "network"
    character_length: int = 300
    attributes: Optional[List[str]] = None

class Data(BaseModel):
    user_url: str
    target_url: str
    intent: str = "network"

def extract_username(linkedin_url: str):
    """Extract username from LinkedIn URL."""
    return urlparse(linkedin_url).path.strip("/").split("/")[-1]

@app.post("/generate-message")
async def generate_message(request: LinkedInRequest, token: str = Depends(oauth2_scheme)):
    """Endpoint to generate LinkedIn connection message."""
    try:
        
        # Extract usernames
        user_username = extract_username(request.user_url)
        target_username = extract_username(request.target_url)

        # Fetch profile data and posts for both user and target
        user_profile = config.get_profile_data(request.user_url)
        #user_data = config.clean_data(user_profile)
        #user_posts = config.get_profile_posts(user_username)

        target_profile = config.get_profile_data(request.target_url)
        #target_data = config.clean_data(target_profile)
        #target_posts = config.get_profile_posts(target_username)
        
        # Generate AI connection message
        message = config.generate_ai_message(
            user_data=user_profile,
            target_data=target_profile,
            intent=request.intent,
            attributes=request.attributes,
            character_length=request.character_length
        )
        # Record the connection request
        await record_connection_request(request, token)
        
        return {"message": message}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
@app.post("/genearte_voice_script")
async def voice_script(request: Data):
    '''Endpoint to generate a voice script message'''
    user_profile = config.get_profile_data(request.user_url)
    target_profile = config.get_profile_data(request.target_url)
    voice_message = config.generate_voice_script(
        user_data=user_profile,
        target_data=target_profile,
        intent=request.intent
    )
    
    return voice_message

@app.post("/record-connection-request")
async def record_connection_request(
    request: LinkedInRequest,
    token: str = Depends(oauth2_scheme)
):
    """Record when a user generates a connection message"""
    try:
        user = supabase.auth.get_user(token).user
        
        # Determine industry
        industry = config.extract_industry(request.target_url)  # Example - extract from target profile
        
        # Insert the connection request
        data = supabase.table("connection_requests").insert({
            "user_id": user.id,
            "target_url": request.target_url,
            "template_used": request.intent,  # Using intent as template for now
            "industry": industry,
            "status": "sent"
        }).execute()
        
        # Update the user's total requests count
        supabase.rpc("increment_total_requests", {"user_id": user.id}).execute()
        
        return {"message": "Request recorded", "request_id": data.data[0]['id']}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    

@app.post("/update-connection-status")
async def update_connection_status(
    update: ConnectionStatusUpdate,
    token: str = Depends(oauth2_scheme)
):
    """Update when a connection is accepted/replied to"""
    try:
        user = supabase.auth.get_user(token).user
        
        # Update the status
        supabase.table("connection_requests").update({
            "status": update.new_status
        }).eq("id", update.request_id).execute()
        
        # Recalculate metrics
        config.calculate_user_metrics(user.id)
        
        return {"message": "Status updated"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/get-metrics")
async def get_metrics(token: str = Depends(oauth2_scheme)):
    """Endpoint to fetch all dashboard metrics"""
    try:
        user = supabase.auth.get_user(token).user
        
        # Get user metrics
        metrics = supabase.table("user_metrics").select("*").eq("user_id", user.id).execute().data[0]
        
        # Get industry metrics
        industry_metrics = supabase.table("industry_metrics").select("*").eq("user_id", user.id).execute().data
        
        # Get template metrics
        template_metrics = supabase.table("template_metrics").select("*").eq("user_id", user.id).execute().data
        
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
    
    
    
@app.post("/signup")
async def signup(user: User):
    try:
        response = supabase.auth.sign_up({"email": user.email, "password": user.password})
        return {"message": "User created successfully", "user": response}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/login")
async def login(user: User):
    try:
        response = supabase.auth.sign_in_with_password({"email": user.email, "password": user.password})
        return {"message": "Logged in successfully", "user": response}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/auth/google")
async def auth_google():
    try:
        # Redirect to Supabase's Google OAuth URL
        auth_url = supabase.auth.sign_in_with_oauth({"provider": "google"})
        return RedirectResponse(url=auth_url.url)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/dashboard")
async def dashboard(token: str = Depends(oauth2_scheme)):
    try:
        user = supabase.auth.get_user(token)
        return {"message": "Welcome to your dashboard", "user": user}
    except Exception as e:
        raise HTTPException(status_code=401, detail="Unauthorized")

@app.get("/")
async def root():
    return {"message": "Welcome to the FastAPI Connecxite backend"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)