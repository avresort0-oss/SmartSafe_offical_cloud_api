from core.database import SessionLocal
from core.models.api_key import ApiKey
from core.models.workspace import Workspace
from core.models.user import User
import argon2

API_KEY = "ss_live_6L4l8t3WI-afrmaHc8oyxShSYE9WQES8uYjZKpgfbvs"
prefix = API_KEY[:8]

db = SessionLocal()
try:
    user = db.query(User).first()
    ws = db.query(Workspace).first()
    if not ws:
        ws = Workspace(name="Default Workspace", owner_id=user.id if user else None)
        db.add(ws)
        db.flush()
    
    ph = argon2.PasswordHasher()
    hashed = ph.hash(API_KEY)
    
    key_rec = db.query(ApiKey).filter(ApiKey.prefix == prefix).first()
    if key_rec:
        key_rec.key_hash = hashed
    else:
        key_rec = ApiKey(
            prefix=prefix,
            key_hash=hashed,
            workspace_id=ws.id,
            label='Phase 4 Test Key'
        )
        db.add(key_rec)
    db.commit()
    print("API_KEY_SYNCED")
finally:
    db.close()
