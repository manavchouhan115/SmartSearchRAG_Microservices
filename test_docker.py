import requests
import json
import time

GATEWAY_URL = "http://127.0.0.1:8000"

def test_docker_flow():
    print("--- 1. Testing Login ---")
    res_login = requests.post(f"{GATEWAY_URL}/auth/login", data={"username": "admin", "password": "password"})
    assert res_login.status_code == 200, "Login failed"
    token = res_login.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    print("Login OK. Token Received.")
    
    print("\n--- 2. Testing Ingestion via Gateway Async Worker ---")
    with open("data/docs/EPA2022.pdf", "rb") as f:
        files = {"file": ("EPA2022.pdf", f, "application/pdf")}
        data = {"collection_name": "docker_collection"}
        res_ingest = requests.post(f"{GATEWAY_URL}/ingest", files=files, data=data, headers=headers)
        
    assert res_ingest.status_code == 200, f"Ingestion Queuing Failed: {res_ingest.text}"
    job_id = res_ingest.json()["job_id"]
    print(f"Queued Successfully! Job ID: {job_id}")
    
    print("\n--- 3. Polling Background Worker Status ---")
    while True:
        res_status = requests.get(f"{GATEWAY_URL}/status/{job_id}", headers=headers).json()
        status = res_status.get("status")
        print(f"Status: {status}")
        if status == "completed":
            print(f"Ingestion Finished! Inserted Chunks: {res_status['result'].get('inserted_count')}")
            break
        elif status == "failed":
            print("Background Task Failed:", res_status.get("error"))
            return
        time.sleep(2)
        
    print("\n--- 4. Testing Query via LangGraph Docker Agent ---")
    payload = {"question": "What key environmental strategies or climate goals were highlighted by the EPA?", "collection_name": "docker_collection"}
    res_query = requests.post(f"{GATEWAY_URL}/query", json=payload, headers=headers)
    
    if res_query.status_code == 200:
        print("\nAgent Output:")
        print(json.dumps(res_query.json(), indent=2))
    else:
        print("Query Failed!", res_query.text)

if __name__ == "__main__":
    test_docker_flow()
