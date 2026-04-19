from fpdf import FPDF
import requests
import json
import time

def create_pdf(filename="sample.pdf"):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", size=12)
    # Adding multiple lines of text to ensure we have enough tokens to chunk and test overlap
    text = (
        "SmartSearch is a revolutionary multi-agent augmented generation platform. "
        "It focuses on optimizing search using lightweight, efficient models instead of heavy monolithic pipelines. "
        "It uses a local ChromaDB for vector storage and uses the HuggingFace Inference API for embeddings, "
        "minimizing RAM footprint and cost. LangGraph acts as the state orchestrator handling various agents like "
        "QueryAnalyser, Retriever, Synthesiser and Critic. "
    ) * 10 
    pdf.multi_cell(0, 10, text)
    pdf.output(filename)
    return filename

def test_ingestion(filename):
    print(f"Uploading {filename} to ingestion service...")
    with open(filename, "rb") as f:
        files = {"file": (filename, f, "application/pdf")}
        data = {"collection_name": "test_collection"}
        response = requests.post("http://127.0.0.1:8002/ingest", files=files, data=data)
    
    print("Ingestion Response Status:", response.status_code)
    try:
        print("Ingestion Response Body:", json.dumps(response.json(), indent=2))
        return response.json()
    except Exception as e:
        print("Failed to decode JSON:", response.text)
        return None

def test_query():
    print("Querying the vector service...")
    # Generate a query embedding using the same model or just mock it.
    # Actually wait, the vector service needs the `query_embeddings` directly, 
    # normally the retriever does this. We'll simply mock a fake embedding array of length 384
    # since all-MiniLM-L6-v2 outputs 384 dimensions.
    
    # We can just fetch the generated embeddings from the database to ensure they are there!
    payload = {
        "collection_name": "test_collection",
        "query_embeddings": [[0.0] * 384],
        "n_results": 2
    }
    response = requests.post("http://127.0.0.1:8001/query", json=payload)
    print("Query Response Status:", response.status_code)
    try:
        print("Query Response Body:", json.dumps(response.json(), indent=2))
    except Exception as e:
        print("Failed to decode JSON:", response.text)

if __name__ == "__main__":
    fn = create_pdf()
    res = test_ingestion(fn)
    if res and res.get("status") == "success":
        time.sleep(1) # Short wait just in case
        test_query()
