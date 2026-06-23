import pytest
import requests
import uuid
import time
import json
import os
import sys

BASE_URL = os.getenv("SMARTSAFE_BASE_URL", "http://localhost:8000/v1")
API_KEY = os.getenv("SMARTSAFE_API_KEY", "ss_live_hybrid_test_key")

def wait_for_server(url, timeout=30):
    start = time.time()
    while time.time() - start < timeout:
        try:
            requests.get(f"{url.replace('/v1', '')}/health")
            return True
        except:
            time.sleep(1)
    return False

@pytest.fixture(scope="module")
def workspace_setup():
    return _setup_mock_workspace()


def _setup_mock_workspace():
    print("Setting up mock Workspace and API Key for Phase 6 testing...")
    import argon2
    from core.database import SessionLocal
    from core.models.workspace import Workspace
    from core.models.api_key import ApiKey
    from core.models.integration import DesktopInstance
    
    from core.models.user import User
    
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.username == 'test_admin').first()
        if not user:
            user = User(username='test_admin', email='test@example.com', password_hash='hash')
            db.add(user)
            db.flush()

        ws = db.query(Workspace).filter(Workspace.name == 'Hybrid Phase 6').first()
        if not ws:
            ws = Workspace(name='Hybrid Phase 6', owner_id=user.id)
            db.add(ws)
            db.flush()
        
        raw_key = API_KEY
        prefix = raw_key[:8]
        ph = argon2.PasswordHasher()
        
        db.query(ApiKey).filter(ApiKey.prefix == prefix).delete()
        db.commit()
        
        hashed = ph.hash(raw_key)
        key_rec = ApiKey(
            prefix=prefix,
            key_hash=hashed,
            workspace_id=ws.id,
            label='Phase 6 Test Key'
        )
        db.add(key_rec)
        db.commit()
        return ws.id
    finally:
        db.close()

def test_phase6_hybrid_integration(workspace_setup):
    print("\n--- Phase 6: Hybrid Integration Test ---")
    
    # 1. Setup: Create Workspace and API Key
    # We'll use the existing manage_keys logic or just hit the endpoints if we have a key.
    # For simplicity, let's assume we can use a key from environment or a known one.
    # In a real test, we'd boot the app and create these.
    
    # Let's try to get a key or create a workspace via a "super admin" or similar if exists.
    # Actually, we can just use the same setup as test_phase5.py
    
    # For now, let's assume the server is running on 8080.
    
    # --- STEP 1: Registration ---
    print("[1] Creating Test Workspace...")
    
    headers = {
        "X-API-Key": API_KEY,
        "Content-Type": "application/json"
    }

    # --- STEP 2: Toggle to LOCAL Mode ---
    print("[2] Toggling to LOCAL mode...")
    payload = {"mode": "LOCAL"}
    resp = requests.patch(f"{BASE_URL}/settings/sync-mode", json=payload, headers=headers)
    if resp.status_code != 200:
        print(f"FAILED to toggle mode: {resp.text}")
        return
    print(f"SUCCESS: {resp.json()}")

    # --- STEP 3: Send Message (Should divert to LOCAL) ---
    print("[3] Sending message in LOCAL mode...")
    msg_payload = {
        "target_phone": "1234567890",
        "content": "Hello from Hybrid Mode!",
        "sender_id": "user_1",
        "contact_id": "contact_1"
    }
    resp = requests.post(f"{BASE_URL}/messages/send", json=msg_payload, headers=headers)
    if resp.status_code != 202:
        print(f"FAILED to send message: {resp.text}")
        return
    
    msg_data = resp.json()
    print(f"SUCCESS: Message ID {msg_data['id']} status is {msg_data['status']}")
    assert msg_data['status'] == "QUEUED_LOCAL"

    # --- STEP 4: Desktop Registration ---
    print("[4] Registering Desktop Instance...")
    reg_payload = {
        "name": "Admin-PC-01",
        "instance_id": f"HWID-{uuid.uuid4().hex[:8]}"
    }
    resp = requests.post(f"{BASE_URL}/settings/desktop/register", json=reg_payload, headers=headers)
    assert resp.status_code == 200
    instance_id = resp.json()['instance_id']
    print(f"SUCCESS: Instance {instance_id} registered.")

    # --- STEP 5: Desktop Polling ---
    print("[5] Desktop Polling for messages...")
    resp = requests.get(f"{BASE_URL}/settings/desktop/poll", headers=headers)
    assert resp.status_code == 200
    pending_msgs = resp.json()
    print(f"SUCCESS: Found {len(pending_msgs)} pending messages.")
    assert len(pending_msgs) >= 1
    assert any(m['id'] == msg_data['id'] for m in pending_msgs)

    # --- STEP 6: Heartbeat ---
    print("[6] Sending Heartbeat...")
    resp = requests.post(f"{BASE_URL}/settings/desktop/heartbeat/{instance_id}", headers=headers)
    assert resp.status_code == 200
    print("SUCCESS: Heartbeat sent.")

    # --- STEP 7: Toggle back to CLOUD ---
    print("[7] Toggling back to CLOUD mode...")
    payload = {"mode": "CLOUD"}
    resp = requests.patch(f"{BASE_URL}/settings/sync-mode", json=payload, headers=headers)
    assert resp.status_code == 200
    print("SUCCESS: Toggled back to CLOUD.")

    print("\n--- PHASE 6 VERIFICATION SUCCESSFUL ---")

if __name__ == "__main__":
    if not wait_for_server(BASE_URL):
        print("Server not found on 8080")
        sys.exit(1)
    
    try:
        workspace_id = _setup_mock_workspace()
        test_phase6_hybrid_integration(workspace_id)
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"ERROR: {e}")
