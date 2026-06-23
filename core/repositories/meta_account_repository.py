import sys
import os
from typing import List, Optional
from datetime import datetime, timezone

# Add project root to sys.path for module discovery
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, project_root)

from sqlalchemy.orm import Session
from core.repository import BaseRepository
from core.models.meta_account import MetaAccount

class MetaAccountRepository(BaseRepository[MetaAccount]):
    """
    Concrete repository for the MetaAccount entity.
    Extends the generic BaseRepository with Meta API specific query methods.
    """
    def __init__(self, session: Session):
        super().__init__(session, MetaAccount)

    def get_by_workspace(self, workspace_id: str, active_only: bool = True) -> List[MetaAccount]:
        """Fetches all Meta accounts associated with a specific workspace."""
        query = self.session.query(self.model_class).filter_by(workspace_id=workspace_id)
        if active_only:
            query = query.filter_by(is_active=True)
        return query.all()

    def get_by_phone_number_id(self, phone_number_id: str) -> Optional[MetaAccount]:
        """Fetches an active account by its unique Meta Phone Number ID."""
        return self.session.query(self.model_class).filter_by(phone_number_id=phone_number_id, is_active=True).first()

    def update_health_status(self, account_id: str, api_status: str, quality_rating: str, verified_name: str, display_phone: str) -> Optional[MetaAccount]:
        """Updates the cached health metrics pinged from the Meta Graph API."""
        account = self.session.query(self.model_class).filter_by(id=account_id).first()
        if account:
            account.api_status = api_status
            account.quality_rating = quality_rating
            if verified_name:
                account.verified_name = verified_name
            if display_phone:
                account.display_phone = display_phone
            account.last_synced_at = datetime.now(timezone.utc)
            self.session.commit()
            self.session.refresh(account)
        return account

    def soft_delete(self, account_id: str) -> bool:
        """Soft deletes an account so we don't orphan previous messages sent by it."""
        account = self.session.query(self.model_class).filter_by(id=account_id).first()
        if account:
            account.is_active = False
            self.session.commit()
            return True
        return False