import pytest
import requests
import time
import sys
import os
BASE_URL = os.getenv("SMARTSAFE_BASE_URL", "http://localhost:8000/v1")
API_KEY = os.getenv("SMARTSAFE_API_KEY", "ss_live_test_key_12345")

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
def account_id():
    return _setup_mock_account()


def _setup_mock_account():
    print("Setting up mock Workspace and API Key for testing...")
    script_path = "setup_test_acc.py"
    try:
        with open(script_path, "w") as f:
            f.write(f"""
from core.database import SessionLocal
from core.models.meta_account import MetaAccount
from core.models.workspace import Workspace
from core.models.user import User
from core.models.api_key import ApiKey
from services.auth_service import AuthService
db = SessionLocal()
try:
    owner = db.query(User).filter(
        (User.username == 'phase5_owner') | (User.email == 'phase5@example.com')
    ).first()
    if not owner:
        owner = User(username='phase5_owner', email='phase5@example.com', password_hash='hash')
        db.add(owner)
        db.flush()

    ws = db.query(Workspace).filter(Workspace.name == 'Enterprise Test').first()
    if not ws:
        ws = Workspace(name='Enterprise Test', owner_id=owner.id)
        db.add(ws)
        db.flush()
    
    # Ensure API Key matches the one in test script
    raw_key = "{API_KEY}"
    prefix = raw_key[:8]
    import argon2
    ph = argon2.PasswordHasher()
    
    # Force recreate to avoid stale hash
    db.query(ApiKey).filter(ApiKey.prefix == prefix).delete()
    db.commit()
    
    hashed = ph.hash(raw_key)
    key_rec = ApiKey(
        prefix=prefix,
        key_hash=hashed,
        workspace_id=ws.id,
        label='Test Key'
    )
    db.add(key_rec)
    db.commit()
    
    # Self-verify
    try:
        ph.verify(key_rec.key_hash, raw_key)
        print("MOCK_KEY_VERIFIED")
    except Exception as exc:
        print(f"MOCK_KEY_FAILED: {{exc}}")

    acc = db.query(MetaAccount).filter(MetaAccount.display_name == 'Mock Test Account').first()
    if not acc:
        acc = MetaAccount(
            id='mock_acc_123',
            display_name='Mock Test Account',
            phone_number_id='123456789',
            waba_id='WABA_ID',
            workspace_id=ws.id,
            access_token='FAKE_TOKEN'
        )
        db.add(acc)
        db.commit()
    print(acc.id)
finally:
    db.close()
""")
        import subprocess
        result = subprocess.run([sys.executable, script_path], capture_output=True, text=True)
        if result.returncode != 0:
            print(f"Setup failed: {result.stderr}")
            return None
        # Only take the last line as the account_id
        lines = result.stdout.strip().splitlines()
        return lines[-1] if lines else None
    finally:
        if os.path.exists(script_path):
            os.remove(script_path)

def test_accounts_health(account_id):
    print(f"\nTesting Account Health Refresh for {account_id}...")
    headers = {"X-API-Key": API_KEY}
    # This will fail at the Meta API call, but we expect a 400 with a specific error from MetaCloudService
    resp = requests.get(f"{BASE_URL}/accounts/{account_id}/health", headers=headers)
    print(f"Status: {resp.status_code}")
    # Since token is FAKE_TOKEN, we expect 400 "Invalid OAuth access token" or similar
    assert resp.status_code in [400, 200] 
    print("Account Health test PASSED (API reached)")

def test_template_sync(account_id):
    print("\nTesting Template Sync Trigger...")
    headers = {"X-API-Key": API_KEY}
    resp = requests.post(f"{BASE_URL}/templates/sync?meta_account_id={account_id}", headers=headers)
    print(f"Status: {resp.status_code}")
    assert resp.status_code == 200
    print("Template Sync Trigger test PASSED")

def test_analytics_summary(account_id):
    print("\nTesting Analytics Summary...")
    headers = {"X-API-Key": API_KEY}
    resp = requests.get(f"{BASE_URL}/analytics/summary", headers=headers)
    print(f"Status: {resp.status_code}")
    assert resp.status_code == 200
    data = resp.json()
    print(f"Summary Data: {data}")
    assert "total" in data
    print("Analytics Summary test PASSED")

def test_analytics_performance(account_id):
    print("\nTesting Analytics Performance...")
    headers = {"X-API-Key": API_KEY}
    resp = requests.get(f"{BASE_URL}/analytics/performance", headers=headers)
    print(f"Status: {resp.status_code}")
    assert resp.status_code == 200
    data = resp.json()
    assert "periodic" in data
    assert "errors" in data
    print("Analytics Performance test PASSED")

if __name__ == "__main__":
    if not wait_for_server(BASE_URL):
        print("Server timed out")
        sys.exit(1)
        
    account_id = _setup_mock_account()
    if not account_id:
        sys.exit(1)
        
    try:
        test_accounts_health(account_id)
        test_template_sync(account_id)
        test_analytics_summary()
        test_analytics_performance()
        print("\nAll Phase 5 integration tests PASSED!")
    except Exception as e:
        print(f"\nTests FAILED: {e}")
        sys.exit(1)
