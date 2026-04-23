from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from .main import run_agent

app = FastAPI(title="SmartSearch Agent Server")

class AgentRequest(BaseModel):
    question: str
    collection_name: str
    thread_id: str

@app.post("/ask")
async def ask_agent(req: AgentRequest):
    try:
        result = run_agent(
            question=req.question,
            collection=req.collection_name,
            thread_id=req.thread_id
        )
        return result
    except Exception as e:
        print("AGENT ERROR:", e)
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health():
    return {"status": "ok"}
