import re
from dataclasses import dataclass
from typing import List, Optional

from sqlalchemy.orm import Session

from core.models.contact import Contact
from core.repositories.contact_repository import ContactRepository


@dataclass
class ContactDTO:
    id: str
    workspace_id: str
    phone_e164: str
    display_name: str
    email: Optional[str]
    lifecycle_stage: str
    owner_user_id: Optional[str]
    notes: str
    is_whatsapp_customer: bool
    is_active: bool


@dataclass
class ContactCreateDTO:
    workspace_id: str
    phone_e164: str
    display_name: str
    email: Optional[str] = None
    lifecycle_stage: str = "LEAD"
    owner_user_id: Optional[str] = None
    notes: str = ""
    is_whatsapp_customer: bool = True


class ContactService:
    def __init__(self, session: Session):
        self.repository = ContactRepository(session)
        self.session = session

    def _normalize_phone(self, raw: str) -> str:
        value = (raw or "").strip()
        has_plus = value.startswith("+")
        digits = re.sub(r"\D", "", value)
        if not digits:
            return ""
        return f"+{digits}" if has_plus or not value.startswith("+") else digits

    def _to_dto(self, entity: Contact) -> ContactDTO:
        return ContactDTO(
            id=entity.id,
            workspace_id=entity.workspace_id,
            phone_e164=entity.phone_e164,
            display_name=entity.display_name,
            email=entity.email,
            lifecycle_stage=entity.lifecycle_stage,
            owner_user_id=entity.owner_user_id,
            notes=entity.notes or "",
            is_whatsapp_customer=entity.is_whatsapp_customer,
            is_active=entity.is_active,
        )

    def list_contacts(self, workspace_id: str) -> List[ContactDTO]:
        return [self._to_dto(c) for c in self.repository.get_by_workspace(workspace_id)]

    def upsert_whatsapp_contact(self, workspace_id: str, phone: str, display_name: str, email: Optional[str] = None) -> ContactDTO:
        normalized = self._normalize_phone(phone)
        entity = self.repository.upsert_whatsapp_contact(workspace_id, normalized, display_name, email)
        return self._to_dto(entity)

    def create_contact(self, dto: ContactCreateDTO) -> ContactDTO:
        normalized = self._normalize_phone(dto.phone_e164)
        if not normalized:
            raise ValueError("Invalid phone number.")
        existing = self.repository.get_by_phone(dto.workspace_id, normalized)
        if existing:
            raise ValueError("Contact already exists for this workspace and phone.")

        entity = Contact(
            workspace_id=dto.workspace_id,
            phone_e164=normalized,
            display_name=dto.display_name.strip() or normalized,
            email=dto.email,
            lifecycle_stage=dto.lifecycle_stage or "LEAD",
            owner_user_id=dto.owner_user_id,
            notes=dto.notes or "",
            is_whatsapp_customer=dto.is_whatsapp_customer,
            is_active=True,
        )
        saved = self.repository.add(entity)
        return self._to_dto(saved)

    def update_contact(self, contact_id: str, **fields) -> Optional[ContactDTO]:
        entity = self.repository.get_by_id(contact_id)
        if not entity:
            return None
        if "display_name" in fields:
            entity.display_name = (fields["display_name"] or entity.display_name).strip()
        if "email" in fields:
            entity.email = fields["email"]
        if "lifecycle_stage" in fields and fields["lifecycle_stage"]:
            entity.lifecycle_stage = fields["lifecycle_stage"]
        if "owner_user_id" in fields:
            entity.owner_user_id = fields["owner_user_id"]
        if "notes" in fields:
            entity.notes = fields["notes"] or ""
        self.session.commit()
        self.session.refresh(entity)
        return self._to_dto(entity)

    def get_contact_by_phone(self, workspace_id: str, phone: str) -> Optional[ContactDTO]:
        normalized = self._normalize_phone(phone)
        entity = self.repository.get_by_phone(workspace_id, normalized)
        return self._to_dto(entity) if entity else None
