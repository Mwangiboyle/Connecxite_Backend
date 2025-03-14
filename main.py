from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from fastapi.responses import RedirectResponse
from supabase import create_client, Client
from pydantic import BaseModel
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

@app.post("/auth/google")
async def auth_google(google_auth: GoogleAuth):
    try:
        # Use Supabase's sign_in_with_oauth method for Google OAuth
        response = supabase.auth.sign_in_with_oauth({"provider": "google", "token": google_auth.token})
        return {"message": "Authentication with Google successful", "user": response}
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