import os
import io
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import JSONResponse
import httpx
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import PyMuPDFLoader
from langchain_huggingface import HuggingFaceEndpointEmbeddings
from dotenv import load_dotenv

load_dotenv()
HF_TOKEN = os.getenv("HF_TOKEN")
if not HF_TOKEN:
    raise ValueError("HF_TOKEN must be set in .env")

# Using a robust free embedding model on the inference API.
embeddings_model = HuggingFaceEndpointEmbeddings(
    model="sentence-transformers/all-MiniLM-L6-v2",
    task="feature-extraction",
    huggingfacehub_api_token=HF_TOKEN
)

app = FastAPI(title="SmartSearch Ingestion Service")
# The Vector service URL internally. We will run it on 8001 locally.
VECTOR_SERVICE_URL = os.getenv("VECTOR_SERVICE_URL", "http://127.0.0.1:8001")

async def get_or_create_collection(collection_name: str):
    async with httpx.AsyncClient() as client:
        # We append name query parameter
        res = await client.post(f"{VECTOR_SERVICE_URL}/collections?name={collection_name}")
        res.raise_for_status()

async def add_to_vector_service(collection_name: str, documents, embeddings, metadatas, ids):
    async with httpx.AsyncClient() as client:
        payload = {
            "collection_name": collection_name,
            "documents": documents,
            "embeddings": embeddings,
            "metadatas": metadatas,
            "ids": ids
        }
        res = await client.post(f"{VECTOR_SERVICE_URL}/add", json=payload)
        res.raise_for_status()
        return res.json()

@app.post("/ingest")
async def ingest_document(
    file: UploadFile = File(...),
    collection_name: str = Form("default"),
):
    if not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")
    
    # Save file temporarily to disk because PyMuPDFLoader requires a filesystem path
    temp_file_path = f"/tmp/{file.filename}"
    os.makedirs("/tmp", exist_ok=True)
    with open(temp_file_path, "wb") as f:
        content = await file.read()
        f.write(content)
        
    try:
        # Parse PDF
        loader = PyMuPDFLoader(temp_file_path)
        docs = loader.load()
        
        # Chunk text
        text_splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
        chunks = text_splitter.split_documents(docs)
        
        if not chunks:
            raise HTTPException(status_code=400, detail="No readable text found in PDF.")

        text_chunks = [chunk.page_content for chunk in chunks]
        
        # Embed text using HF API
        print(f"Embedding {len(text_chunks)} chunks...")
        embedded_chunks = embeddings_model.embed_documents(text_chunks)
        
        # Add to Vector service
        metadatas = [{"source": file.filename, "page": chunk.metadata.get("page", 0)} for chunk in chunks]
        ids = [f"{file.filename}-chunk-{i}" for i in range(len(chunks))]
        
        print("Ensuring collection exists...")
        await get_or_create_collection(collection_name)
        
        print("Adding to vector DB in batches...")
        batch_size = 500
        last_res = None
        for i in range(0, len(text_chunks), batch_size):
            batch_docs = text_chunks[i:i+batch_size]
            batch_embs = embedded_chunks[i:i+batch_size]
            batch_meta = metadatas[i:i+batch_size]
            batch_ids = ids[i:i+batch_size]
            print(f"Uploading batch {i} out of {len(text_chunks)}...")
            last_res = await add_to_vector_service(
                collection_name=collection_name,
                documents=batch_docs,
                embeddings=batch_embs,
                metadatas=batch_meta,
                ids=batch_ids
            )
        
        return JSONResponse(content={
            "status": "success",
            "message": f"Successfully ingested {file.filename}",
            "chunks_processed": len(text_chunks),
            "vector_service_response": last_res
        })

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)

@app.get("/health")
async def health():
    return {"status": "ok"}
