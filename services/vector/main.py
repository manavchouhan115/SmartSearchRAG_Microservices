from fastapi import FastAPI, HTTPException
import chromadb
from pydantic import BaseModel
from typing import List

app = FastAPI(title="SmartSearch Vector Service")

# Use lightweight persistent client. This saves its data locally to ./data/chroma
client = chromadb.PersistentClient(path="./data/chroma")

class AddRequest(BaseModel):
    collection_name: str
    documents: List[str]
    embeddings: List[List[float]]
    metadatas: List[dict]
    ids: List[str]

class QueryRequest(BaseModel):
    collection_name: str
    query_embeddings: List[List[float]]
    n_results: int = 5

@app.post("/collections")
async def create_or_get_collection(name: str):
    try:
        col = client.get_or_create_collection(name=name)
        return {"status": "success", "collection": name}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/add")
async def add_documents(req: AddRequest):
    try:
        col = client.get_collection(req.collection_name)
        col.add(
            documents=req.documents,
            embeddings=req.embeddings,
            metadatas=req.metadatas,
            ids=req.ids
        )
        return {"status": "success", "inserted_count": len(req.ids)}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=f"Collection not found: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/query")
async def query_documents(req: QueryRequest):
    try:
        col = client.get_collection(req.collection_name)
        results = col.query(
            query_embeddings=req.query_embeddings,
            n_results=req.n_results
        )
        # Format the response clearly
        return {
            "documents": results["documents"][0] if results["documents"] else [],
            "distances": results["distances"][0] if results["distances"] else [],
            "metadatas": results["metadatas"][0] if results["metadatas"] else []
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=f"Collection not found: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health():
    return {"status": "ok"}
