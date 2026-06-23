import os
import sys
import threading
import time
import requests
import pytest
import uvicorn
import shutil

# Override DATABASE_URL before importing anything else
test_db_path = "./test_smartsafe.db"
os.environ["DATABASE_URL"] = f"sqlite:///{test_db_path}"

# Add project root to path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

def run_server():
    uvicorn.run("api_main:app", host="127.0.0.1", port=8000, log_level="warning")

@pytest.fixture(scope="session", autouse=True)
def fastapi_server():
    # Remove existing test DB if any
    if os.path.exists(test_db_path):
        os.remove(test_db_path)
    if os.path.exists(test_db_path + "-shm"):
        os.remove(test_db_path + "-shm")
    if os.path.exists(test_db_path + "-wal"):
        os.remove(test_db_path + "-wal")

    # Initialize the test schema
    from core.database import init_db, engine
    init_db()

    # Check if server is already running on port 8000
    try:
        resp = requests.get("http://127.0.0.1:8000/health", timeout=1)
        if resp.status_code == 200:
            print("\n[conftest] FastAPI server is already running on port 8000.")
            yield
            # Cleanup test db
            if os.path.exists(test_db_path):
                try:
                    os.remove(test_db_path)
                    os.remove(test_db_path + "-shm")
                    os.remove(test_db_path + "-wal")
                except:
                    pass
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
    
    # Cleanup test db
    try:
        if engine:
            engine.dispose()
        if os.path.exists(test_db_path):
            os.remove(test_db_path)
        if os.path.exists(test_db_path + "-shm"):
            os.remove(test_db_path + "-shm")
        if os.path.exists(test_db_path + "-wal"):
            os.remove(test_db_path + "-wal")
    except Exception as e:
        print(f"Failed to cleanup test db: {e}")
