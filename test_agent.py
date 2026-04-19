import os
import requests
import time
from services.agent.main import run_agent

def ingest_doc(filepath, collection_name):
    print(f"Uploading {filepath} to ingestion service...")
    with open(filepath, "rb") as f:
        files = {"file": (os.path.basename(filepath), f, "application/pdf")}
        data = {"collection_name": collection_name}
        response = requests.post("http://127.0.0.1:8002/ingest", files=files, data=data)
    
    print("Ingestion Response HTTP Status:", response.status_code)
    return response.json()

if __name__ == "__main__":
    collection = "reports_collection"
    doc_path = "data/docs/DOT2022.pdf"
    
    # 1. Ingest
    res = ingest_doc(doc_path, collection)
    print("Ingestion Details:", res)
    
    time.sleep(2) # Give it a second
    
    # 2. Query Agent
    print("\n\n------------- AGENT TEST -------------")
    question = "What were the key achievements or initiatives mentioned in the DOT report?"
    print(f"Question: {question}")
    
    agent_output = run_agent(question=question, collection=collection, thread_id="test_thread_dot")
    
    print("\n=== AGENT RESPONSE ===")
    print(agent_output["answer"])
    print(f"\nConfidence: {agent_output['confidence']}")
    print(f"Retries: {agent_output['retries']}")
