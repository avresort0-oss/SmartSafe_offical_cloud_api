import os
import sys

project_root = os.path.abspath(os.path.dirname(__file__))
sys.path.insert(0, project_root)

from sqlalchemy.orm import Session
from core.database import SessionLocal, init_db
from core.models.workspace import Workspace
from core.models.meta_account import MetaAccount

init_db()

with SessionLocal() as session:
    ws = session.query(Workspace).first()
    if not ws:
        print("No workspace found!")
        sys.exit(1)
        
    print(f"Adding Meta Account 'Koren' to workspace {ws.id}")
    koren = session.query(MetaAccount).filter_by(workspace_id=ws.id, display_name="Koren").first()
    if not koren:
        koren = MetaAccount(
            display_name="Koren",
            phone_number_id="123456789",
            waba_id="987654321",
            workspace_id=ws.id,
            display_phone="+1234567890",
            verified_name="Koren",
            quality_rating="GREEN",
            api_status="CONNECTED",
            is_active=True
        )
        koren.access_token = "mock_token"
        session.add(koren)
        session.commit()
        print("Successfully added Koren.")
    else:
        print("Koren profile already exists.")
