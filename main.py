from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from fastapi.responses import RedirectResponse
from supabase import create_client, Client
from pydantic import BaseModel
from urllib.parse import urlparse
from typing import List, Optional
import config
import os
from dotenv import load_dotenv

load_dotenv()

app = FastAPI()

from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://linkedin-connection-enhancer-2.onrender.com/"],  # Replace with your frontend URL
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

class GoogleAuth(BaseModel):
    token: str
    
class LinkedInRequest(BaseModel):
    user_url: str
    target_url: str
    intent: str = "network"
    character_length: int = 300
    attributes: Optional[List[str]] = None

def extract_username(linkedin_url: str):
    """Extract username from LinkedIn URL."""
    return urlparse(linkedin_url).path.strip("/").split("/")[-1]

@app.post("/generate-message")
async def generate_message(request: LinkedInRequest):
    """Endpoint to generate LinkedIn connection message."""
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

    return {"message": message}

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
    return {"message": "Welcome to the FastAPI Supabase Auth Example"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)