import os
import sys
import argparse
from sqlalchemy.orm import Session

# Ensure project root is in path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.database import SessionLocal
from services.auth_service import AuthService
from core.models.workspace import Workspace

def create_key(workspace_name: str, label: str):
    db = SessionLocal()
    try:
        # Find or create workspace
        workspace = db.query(Workspace).filter(Workspace.name == workspace_name).first()
        if not workspace:
            from core.models.user import User
            owner = db.query(User).first() # Just pick the first user for setup
            if not owner:
                print("Error: No users found in database. Create a user first.")
                return
                
            workspace = Workspace(name=workspace_name, owner_id=owner.id)
            db.add(workspace)
            db.flush()
            print(f"Created new workspace: {workspace_name} ({workspace.id}) owned by {owner.username}")
        
        raw_key, api_key_model = AuthService.generate_api_key(workspace.id, label)
        db.add(api_key_model)
        db.commit()
        
        print("\n" + "="*50)
        print("API KEY GENERATED SUCCESSFULLY")
        print("="*50)
        print(f"Workspace: {workspace_name}")
        print(f"Label:     {label}")
        print(f"API Key:   {raw_key}")
        print("="*50)
        print("SAVE THIS KEY NOW. It will never be shown again in plain text.")
        print("="*50 + "\n")
        
    finally:
        db.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="SmartSafe API Key Management")
    parser.add_argument("--workspace", required=True, help="Workspace name")
    parser.add_argument("--label", default="Testing Key", help="Key label")
    
    args = parser.parse_args()
    create_key(args.workspace, args.label)
