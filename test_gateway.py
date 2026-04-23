import requests
import json
import time

GATEWAY_URL = "http://127.0.0.1:8000"

def test_unauthorized_query():
    print("Testing unauthorized /query access...")
    res = requests.post(f"{GATEWAY_URL}/query", json={"question": "What is SmartSearch?", "collection_name": "test_collection"})
    print("Status:", res.status_code)
    assert res.status_code == 401, "Should be rejected with 401 Unauthorized"

def login():
    print("Testing /auth/login...")
    data = {"username": "admin", "password": "password"}
    res = requests.post(f"{GATEWAY_URL}/auth/login", data=data)
    print("Login Status:", res.status_code)
    assert res.status_code == 200, "Login failed!"
    return res.json()["access_token"]

def test_query(token):
    print("Testing active /query with valid JWT...")
    headers = {"Authorization": f"Bearer {token}"}
    payload = {"question": "What are the accomplishments mentioned in DOT report?", "collection_name": "reports_collection"}
    res = requests.post(f"{GATEWAY_URL}/query", json=payload, headers=headers)
    print("Query Status:", res.status_code)
    if res.status_code == 200:
        print("\nGateway Response JSON:")
        print(json.dumps(res.json(), indent=2))
    else:
        print(res.text)

if __name__ == "__main__":
    test_unauthorized_query()
    time.sleep(1)
    
    token = login()
    time.sleep(1)
    
    test_query(token)
