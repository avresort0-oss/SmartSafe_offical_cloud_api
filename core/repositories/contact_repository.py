from typing import List, Optional

from sqlalchemy.orm import Session

from core.models.contact import Contact
from core.repository import BaseRepository


class ContactRepository(BaseRepository[Contact]):
    def __init__(self, session: Session):
        super().__init__(session, Contact)

    def get_by_workspace(self, workspace_id: str, active_only: bool = True) -> List[Contact]:
        query = self.session.query(self.model_class).filter(self.model_class.workspace_id == workspace_id)
        if active_only:
            query = query.filter(self.model_class.is_active == True)
        return query.order_by(self.model_class.updated_at.desc()).all()

    def get_by_phone(self, workspace_id: str, phone_e164: str) -> Optional[Contact]:
        return (
            self.session.query(self.model_class)
            .filter(self.model_class.workspace_id == workspace_id, self.model_class.phone_e164 == phone_e164)
            .first()
        )

    def upsert_whatsapp_contact(self, workspace_id: str, phone_e164: str, display_name: str, email: Optional[str] = None) -> Contact:
        existing = self.get_by_phone(workspace_id, phone_e164)
        if existing:
            if display_name and existing.display_name != display_name:
                existing.display_name = display_name
            if email and existing.email != email:
                existing.email = email
            existing.is_whatsapp_customer = True
            existing.is_active = True
            self.session.commit()
            self.session.refresh(existing)
            return existing

        contact = Contact(
            workspace_id=workspace_id,
            phone_e164=phone_e164,
            display_name=display_name or phone_e164,
            email=email,
            is_whatsapp_customer=True,
            lifecycle_stage="LEAD",
            is_active=True,
        )
        self.session.add(contact)
        self.session.commit()
        self.session.refresh(contact)
        return contact
