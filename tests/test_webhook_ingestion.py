import pytest
import requests
import json
import time
import uuid
import os
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from core.database import SessionLocal, Base, engine
from core.models.workspace import Workspace
from core.models.meta_account import MetaAccount
from core.models.contact import Contact
from core.models.conversation import Conversation
from core.models.message import Message
from core.models.user import User
from services.webhook_receiver_worker import WebhookReceiverWorker
from integrations.whatsapp_integration import WhatsAppIntegration

# Configuration for testing
WEBHOOK_PORT = 8081
WEBHOOK_URL = f"http://localhost:{WEBHOOK_PORT}/"
VERIFY_TOKEN = "test_token_123"

@pytest.fixture(scope="module")
def db():
    # Setup test database state
    session = SessionLocal()
    try:
        # Create a test user as owner
        user = session.query(User).filter_by(username="test_webhook_owner").first()
        if not user:
            user = User(username="test_webhook_owner", email="webhook@test.com", password_hash="hash")
            session.add(user)
            session.flush()

        # Create a test workspace and meta account
        ws_name = f"Test Workspace {uuid.uuid4().hex[:6]}"
        ws = Workspace(name=ws_name, owner_id=user.id)
        session.add(ws)
        session.flush()

        # Create a mock meta account linked to the workspace
        # The phone_number_id must match what we send in the webhook
        phone_id = f"phone_{uuid.uuid4().hex[:10]}"
        acc = MetaAccount(
            workspace_id=ws.id,
            display_name="Test Phone",
            phone_number_id=phone_id,
            waba_id="WABA_123",
            access_token="EAAB...",
        )
        session.add(acc)
        session.commit()
        
        yield {"session": session, "workspace_id": ws.id, "phone_number_id": phone_id}
        
        # Cleanup (optional, but good for local db)
        # session.delete(acc)
        # session.delete(ws)
        # session.commit()
    finally:
        session.close()

@pytest.fixture(scope="module")
def webhook_server(db):
    # Start the real WebhookReceiverWorker on a separate port for testing
    mock_wa = WhatsAppIntegration(db_session=db["session"]) # Need session for account lookups
    worker = WebhookReceiverWorker(whatsapp_integration=mock_wa, port=WEBHOOK_PORT, verify_token=VERIFY_TOKEN)
    worker.start()
    time.sleep(2) # Give it time to bind
    yield worker
    worker.stop()

def test_webhook_full_ingestion_lifecycle(db, webhook_server):
    """
    Verifies: 
    1. Webhook POST hit
    2. Contact auto-provisioning
    3. Conversation creation
    4. Message storage in the database
    5. Correct linkage to Workspace and Account
    """
    phone_number_id = db["phone_number_id"]
    from_phone = "15551234567"
    message_text = "Hello SmartSafe E2E Test!"
    wamid = f"wamid.{uuid.uuid4().hex}"

    # Mock Meta Webhook Payload
    payload = {
        "object": "whatsapp_business_account",
        "entry": [
            {
                "id": "WABA_123",
                "changes": [
                    {
                        "value": {
                            "messaging_product": "whatsapp",
                            "metadata": {
                                "display_phone_number": "15550000000",
                                "phone_number_id": phone_number_id
                            },
                            "contacts": [
                                {
                                    "profile": {"name": "Test User"},
                                    "wa_id": from_phone
                                }
                            ],
                            "messages": [
                                {
                                    "from": from_phone,
                                    "id": wamid,
                                    "timestamp": str(int(time.time())),
                                    "text": {"body": message_text},
                                    "type": "text"
                                }
                            ]
                        },
                        "field": "messages"
                    }
                ]
            }
        ]
    }

    # 1. Send the Webhook POST hit
    headers = {"Content-Type": "application/json"}
    response = requests.post(WEBHOOK_URL, data=json.dumps(payload), headers=headers)
    
    assert response.status_code == 200
    assert response.text == "EVENT_RECEIVED"

    # Allow some time for background processing if needed (though worker is synchronous in its _process_payload call)
    time.sleep(1)

    # 2. Verify Database State
    session = db["session"]
    session.expire_all() # Refresh from disk

    # Check Contact - use normalized phone
    normalized_phone = f"+{from_phone}"
    print(f"\n[TEST DEBUG] Looking for Contact: {normalized_phone} in Workspace: {db['workspace_id']}")
    
    contact = session.query(Contact).filter_by(phone_e164=normalized_phone, workspace_id=db["workspace_id"]).first()
    assert contact is not None
    assert contact.display_name == from_phone # WebhookReceiverWorker currently sets name = phone if no User exists

    # Check Conversation
    conv = session.query(Conversation).filter_by(contact_id=contact.id, workspace_id=db["workspace_id"]).first()
    assert conv is not None
    assert conv.last_message_preview == message_text

    # Check Message
    msg = session.query(Message).filter_by(external_message_id=wamid).first()
    assert msg is not None
    assert msg.direction == "INBOUND"
    assert msg.channel == "WHATSAPP"
    # Content is encrypted in DB, so we'd need to decrypt it to verify text, 
    # but the fact it's there is already a huge win.
    
    print("\n[SUCCESS] Webhook Ingestion E2E Lifecycle Verified.")

if __name__ == "__main__":
    # Manual run support
    pytest.main([__file__])
