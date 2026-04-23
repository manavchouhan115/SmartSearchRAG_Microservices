import os
import uuid
from typing import Dict
from datetime import datetime, timedelta
from fastapi import FastAPI, Depends, HTTPException, status, UploadFile, File, Form, BackgroundTasks
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
import bcrypt
from pydantic import BaseModel
import httpx
from dotenv import load_dotenv

load_dotenv()

# Config
SECRET_KEY = os.getenv("JWT_SECRET", "super-secret-key-for-local-dev-only")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60

INGESTION_SERVICE_URL = os.getenv("INGESTION_SERVICE_URL", "http://127.0.0.1:8002")
AGENT_SERVICE_URL = os.getenv("AGENT_SERVICE_URL", "http://127.0.0.1:8003")

# Mock Auth state
def get_password_hash(password: str):
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

MOCK_USER_DB = {
    "admin": {
        "username": "admin",
        "hashed_password": get_password_hash("password"),
    }
}

app = FastAPI(title="SmartSearch API Gateway")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")

# In-Memory Background Job Tracking
jobs: Dict[str, dict] = {}

# --- Auth Utils ---
def verify_password(plain_password, hashed_password):
    return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

async def get_current_user(token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    
    user = MOCK_USER_DB.get(username)
    if user is None:
        raise credentials_exception
    return user

# --- Auth Endpoints ---
@app.post("/auth/login")
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    user = MOCK_USER_DB.get(form_data.username)
    if not user or not verify_password(form_data.password, user["hashed_password"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token = create_access_token(data={"sub": user["username"]})
    return {"access_token": access_token, "token_type": "bearer"}

# --- Proxy Mechanics ---
async def process_ingestion(job_id: str, file_content: bytes, filename: str, collection_name: str):
    jobs[job_id]["status"] = "processing"
    try:
        async with httpx.AsyncClient() as client:
            files = {"file": (filename, file_content, "application/pdf")}
            data = {"collection_name": collection_name}
            # Timeout is extended because HF Embeddings model overhead
            res = await client.post(f"{INGESTION_SERVICE_URL}/ingest", files=files, data=data, timeout=180.0)
            res.raise_for_status()
            jobs[job_id]["status"] = "completed"
            jobs[job_id]["result"] = res.json()
    except Exception as e:
        jobs[job_id]["status"] = "failed"
        jobs[job_id]["error"] = str(e)


# --- Exposed Service Endpoints ---
@app.post("/ingest")
async def ingest_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    collection_name: str = Form("default"),
    current_user: dict = Depends(get_current_user)
):
    if not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")
        
    job_id = str(uuid.uuid4())
    content = await file.read()
    
    jobs[job_id] = {
        "status": "pending",
        "file": file.filename,
        "started_at": datetime.utcnow().isoformat()
    }
    
    # Delegate to Async Worker
    background_tasks.add_task(process_ingestion, job_id, content, file.filename, collection_name)
    
    return {
        "job_id": job_id,
        "message": "Ingestion task queued successfully. Check /status endpoint.",
        "status": "pending"
    }

@app.get("/status/{job_id}")
async def get_status(job_id: str, current_user: dict = Depends(get_current_user)):
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    return jobs[job_id]

class QueryRequest(BaseModel):
    question: str
    collection_name: str = "default"

@app.post("/query")
async def query_system(req: QueryRequest, current_user: dict = Depends(get_current_user)):
    try:
        thread_id = f"{current_user['username']}_searches"
        
        async with httpx.AsyncClient() as client:
            payload = {
                "question": req.question,
                "collection_name": req.collection_name,
                "thread_id": thread_id
            }
            res = await client.post(f"{AGENT_SERVICE_URL}/ask", json=payload, timeout=120.0)
            res.raise_for_status()
            return res.json()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
