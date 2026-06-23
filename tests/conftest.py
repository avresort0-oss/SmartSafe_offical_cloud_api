import os
import sys
import threading
import time
import requests
import pytest
import uvicorn

# Add project root to path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

def run_server():
    uvicorn.run("api_main:app", host="127.0.0.1", port=8000, log_level="warning")

@pytest.fixture(scope="session", autouse=True)
def fastapi_server():
    # Check if server is already running on port 8000
    try:
        resp = requests.get("http://127.0.0.1:8000/health", timeout=1)
        if resp.status_code == 200:
            print("\n[conftest] FastAPI server is already running on port 8000.")
            yield
            return
    except requests.exceptions.RequestException:
        pass

    print("\n[conftest] Starting background FastAPI server on port 8000...")
    thread = threading.Thread(target=run_server, daemon=True)
    thread.start()
    
    # Wait for the server to be ready
    for i in range(20):
        try:
            resp = requests.get("http://127.0.0.1:8000/health", timeout=1)
            if resp.status_code == 200:
                print(f"[conftest] FastAPI server is ready after {i * 0.5} seconds.")
                break
        except requests.exceptions.RequestException:
            pass
        time.sleep(0.5)
    else:
        raise RuntimeError("FastAPI server failed to start for integration tests")
        
    yield
