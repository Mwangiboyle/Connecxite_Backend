from fastapi import FastAPI, Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from urllib.parse import urlparse
from typing import List, Optional
import asyncpg
import config
import jwt
import uuid
import os
from contextlib import asynccontextmanager
from dotenv import load_dotenv

load_dotenv()

# Connection pool setup
pool = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize the connection pool when app starts
    global pool
    pool = await asyncpg.create_pool(
        database=os.getenv("DB_NAME", "your_database"),
        user=os.getenv("DB_USER", "your_user"),
        password=os.getenv("DB_PASSWORD", "your_password"),
        host=os.getenv("DB_HOST", "your_vps_ip"),
        port=os.getenv("DB_PORT", "5432"),
        min_size=5,  # Minimum number of connections
        max_size=20,  # Maximum number of connections
        max_inactive_connection_lifetime=300  # Recycle connections after 5 minutes
    )
    yield
    # Close the connection pool when app shuts down
    await pool.close()

app = FastAPI(
    title="Connecxite backend. made with FastAPI",
    lifespan=lifespan
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://linkedin-connection-enhancer-2.onrender.com", "http://localhost:4000","http://localhost:8000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
# Database connection function
@asynccontextmanager
async def get_db_connection():
    connection = await pool.acquire()
    try:
        yield connection
    finally:
        await pool.release(connection)

SECRET_KEY = os.getenv("DJANGO_SECRET_KEY")
security = HTTPBearer()
ALGORITHM = "HS256"


SECRET_KEY = os.getenv("DJANGO_SECRET_KEY")
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

        await record_connection_request(request, payload)
        return {"message": message}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/record-connection-request")
async def record_connection_request(request: LinkedInRequest, payload: dict = Depends(verify_token)):
    async with get_db_connection() as conn:
        try:
            user_id = payload.get("user_id")
            industry = config.extract_industry(request.target_url)
            target_url = request.target_url

            # Insert connection request
            request_id = await conn.fetchval("""
                INSERT INTO connection_requests 
                (user_id, target_url, template_used, industry, status)
                VALUES ($1, $2, $3, $4, 'sent')
                RETURNING id
            """, user_id, target_url, request.intent, industry)
            
            # Initialize or update user metrics
            await conn.execute("""
                INSERT INTO user_metrics (user_id, total_requests)
                VALUES ($1, 1)
                ON CONFLICT (user_id) 
                DO UPDATE SET 
                    total_requests = user_metrics.total_requests + 1,
                    last_updated = NOW()
            """, user_id)

            # Call the calculate functions
            await conn.execute("SELECT calculate_acceptance_rate($1)", user_id)
            await conn.execute("SELECT calculate_response_rate($1)", user_id)
            await conn.execute("SELECT calculate_industry_metrics($1)", user_id)
            await conn.execute("SELECT calculate_template_metrics($1)", user_id)

            return {"message": "Request recorded", "request_id": request_id}
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))

@app.post("/update-connection-status")
async def update_connection_status(update: ConnectionStatusUpdate, payload: dict = Depends(verify_token)):
    async with get_db_connection() as conn:
        try:
            user_id = payload.get("user_id")
            
            # Update status
            await conn.execute("""
                UPDATE connection_requests
                SET status = $1
                WHERE id = $2
            """, update.new_status, update.request_id)

            # Recalculate all metrics
            await conn.execute("SELECT calculate_acceptance_rate($1)", user_id)
            await conn.execute("SELECT calculate_response_rate($1)", user_id)
            await conn.execute("SELECT calculate_industry_metrics($1)", user_id)
            await conn.execute("SELECT calculate_template_metrics($1)", user_id)

            return {"message": "Status updated"}
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))

@app.get("/get-metrics")
async def get_metrics(payload: dict = Depends(verify_token)):
    async with get_db_connection() as conn:
        try:
            user_id = payload.get("user_id")
            
            # Get metrics data
            metrics = await conn.fetchrow(
                "SELECT * FROM user_metrics WHERE user_id = $1", 
                user_id
            )
            
            industry_metrics = await conn.fetch(
                "SELECT * FROM industry_metrics WHERE user_id = $1", 
                user_id
            )
            
            template_metrics = await conn.fetch(
                "SELECT * FROM template_metrics WHERE user_id = $1", 
                user_id
            )

            # Handle case where metrics don't exist yet
            if not metrics:
                return {
                    "connection_requests": 0,
                    "acceptance_rate": 0,
                    "active_conversations": 0,
                    "response_rate": 0,
                    "industries": {},
                    "templates": {}
                }

            return {
                "connection_requests": metrics.get("total_requests", 0),
                "acceptance_rate": metrics.get("acceptance_rate", 0),
                "active_conversations": metrics.get("active_conversations", 0),
                "response_rate": metrics.get("response_rate", 0),
                "industries": {im["industry"]: im["success_rate"] for im in industry_metrics},
                "templates": {tm["template_name"]: tm["success_rate"] for tm in template_metrics}
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

@app.get("/list-functions")
async def list_functions():
    async with get_db_connection() as conn:
        functions = await conn.fetch("""
            SELECT 
                n.nspname as schema,
                p.proname as function_name,
                pg_get_function_result(p.oid) as return_type,
                pg_get_function_arguments(p.oid) as arguments
            FROM 
                pg_proc p
            LEFT JOIN 
                pg_namespace n ON p.pronamespace = n.oid
            WHERE 
                n.nspname NOT IN ('pg_catalog', 'information_schema')
            ORDER BY 
                schema, function_name;
        """)
        return [dict(func) for func in functions]
    

@app.get("/selected-table-columns")
async def get_selected_table_columns():
    selected_tables = ["connection_requests","industry_metrics", "user_metrics", "template_metrics"]

    async with get_db_connection() as conn:
        columns_info = {}

        for table in selected_tables:
            rows = await conn.fetch("""
                SELECT column_name, data_type
                FROM information_schema.columns
                WHERE table_name = $1
                ORDER BY ordinal_position;
            """, table)
            columns_info[table] = [dict(row) for row in rows]

        return columns_info


@app.get("/")
async def root():
    return {"message": "Welcome to the FastAPI Connecxite backend"}
