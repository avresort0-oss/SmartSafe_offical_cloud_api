import requests
import time
import sys
import os
import pytest
from core.database import SessionLocal
from core.models.api_key import ApiKey
from core.models.workspace import Workspace
from core.models.user import User
import argon2

BASE_URL = os.getenv("SMARTSAFE_MESSAGES_BASE_URL", "http://127.0.0.1:8000/v1/messages")
API_KEY = os.getenv("SMARTSAFE_API_KEY", "ss_live_6L4l8t3WI-afrmaHc8oyxShSYE9WQES8uYjZKpgfbvs")

@pytest.fixture(scope="module", autouse=True)
def setup_api_key():
    db = SessionLocal()
    try:
        user = db.query(User).first()
        if not user:
            user = User(username="default_user", email="default@example.com", password_hash="hash")
            db.add(user)
            db.flush()
            
        ws = db.query(Workspace).first()
        if not ws:
            ws = Workspace(name="Default Workspace", owner_id=user.id)
            db.add(ws)
            db.flush()
            
        prefix = API_KEY[:8]
        ph = argon2.PasswordHasher()
        hashed = ph.hash(API_KEY)
        
        # Clear out any old records with this prefix
        db.query(ApiKey).filter(ApiKey.prefix == prefix).delete()
        db.commit()
        
        key_rec = ApiKey(
            prefix=prefix,
            key_hash=hashed,
            workspace_id=ws.id,
            label='Phase 4 Test Key'
        )
        db.add(key_rec)
        db.commit()
    finally:
        db.close()

def wait_for_server(url, timeout=10):
    health_url = f"{url.split('/v1/')[0]}/health" if "/v1/" in url else f"{url.replace('/v1', '')}/health"
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            requests.get(health_url)
            print("Server is UP")
            return True
        except:
            time.sleep(1)
    return False

def test_unauthorized():
    print("Testing unauthorized request...")
    resp = requests.post(f"{BASE_URL}/send", json={
        "target_phone": "1234567890",
        "content": "No key test",
        "sender_id": "test_user",
        "contact_id": "test_contact"
    })
    print(f"Status: {resp.status_code}")
    assert resp.status_code == 401
    print("Unauthorized test PASSED")

def test_authorized():
    print("\nTesting authorized request...")
    headers = {"X-API-Key": API_KEY}
    payload = {
        "target_phone": "1234567890",
        "content": "Authorized test",
        "sender_id": "test_user",
        "contact_id": "test_contact"
    }
    resp = requests.post(f"{BASE_URL}/send", headers=headers, json=payload)
    print(f"Status: {resp.status_code}")
    print(f"Response: {resp.text}")
    assert resp.status_code == 202
    print("Authorized test PASSED")

def test_rate_limit():
    print("\nTesting rate limit (this may take a moment)...")
    headers = {"X-API-Key": API_KEY}
    payload = {
        "target_phone": "1234567890",
        "content": "Rate limit test",
        "sender_id": "test_user",
        "contact_id": "test_contact"
    }
    # We set limit to 100 per minute. Let's try to burst 105.
    success_count = 0
    blocked_count = 0
    for i in range(105):
        resp = requests.post(f"{BASE_URL}/send", headers=headers, json=payload)
        if resp.status_code == 202:
            success_count += 1
        elif resp.status_code == 429:
            blocked_count += 1
            break # Got rate limited
    
    print(f"Successes: {success_count}, Blocked: {blocked_count}")
    assert blocked_count > 0
    print("Rate limit test PASSED")

if __name__ == "__main__":
    if not wait_for_server(BASE_URL):
        print("Server timed out")
        sys.exit(1)
        
    try:
        test_unauthorized()
        test_authorized()
        test_rate_limit()
        print("\nAll integration tests PASSED!")
    except Exception as e:
        print(f"\nTests FAILED: {e}")
        sys.exit(1)
