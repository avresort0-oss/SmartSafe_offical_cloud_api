from typing import List, Optional

from sqlalchemy import or_
from sqlalchemy.orm import Session, joinedload, selectinload

from core.models.contact import Contact
from core.models.conversation import Conversation
from core.models.label import Label
from core.repository import BaseRepository


class ConversationRepository(BaseRepository[Conversation]):
    def __init__(self, session: Session):
        super().__init__(session, Conversation)

    def list_by_workspace(
        self,
        workspace_id: str,
        search: str = "",
        status: Optional[str] = None,
        assigned_user_id: Optional[str] = None,
        label_query: Optional[str] = None,
        unread_only: bool = False,
        meta_account_id: Optional[str] = None,
        archived: bool = False,
        limit: int = 200,
        offset: int = 0,
    ) -> List[Conversation]:
        query = (
            self.session.query(self.model_class)
            .options(
                joinedload(self.model_class.contact).selectinload(Contact.labels),
                joinedload(self.model_class.assigned_user),
                selectinload(self.model_class.labels),
            )
            .filter(self.model_class.workspace_id == workspace_id)
            .filter(self.model_class.is_archived == archived)
            .filter(self.model_class.is_deleted == False)
        )
        if status:
            query = query.filter(self.model_class.status == status)
        if assigned_user_id:
            query = query.filter(self.model_class.assigned_user_id == assigned_user_id)
        if meta_account_id:
            query = query.filter(self.model_class.meta_account_id == meta_account_id)
        if label_query:
            label_term = f"%{label_query.strip()}%"
            query = query.filter(
                or_(
                    Conversation.labels.any(Label.name.ilike(label_term)),
                    Conversation.contact.has(Contact.labels.any(Label.name.ilike(label_term))),
                )
            )
        if unread_only:
            query = query.filter(self.model_class.unread_count > 0)
        if search:
            query = query.join(self.model_class.contact).filter(
                or_(
                    Conversation.last_message_preview.ilike(f"%{search}%"),
                    Contact.display_name.ilike(f"%{search}%"),
                    Contact.phone_e164.ilike(f"%{search}%"),
                )
            )
        return (
            query.order_by(self.model_class.is_pinned.desc(), self.model_class.updated_at.desc())
            .distinct()
            .limit(limit)
            .offset(offset)
            .all()
        )

    def get_by_workspace_and_contact(self, workspace_id: str, contact_id: str, meta_account_id: Optional[str] = None) -> Optional[Conversation]:
        query = self.session.query(self.model_class).filter(
            self.model_class.workspace_id == workspace_id,
            self.model_class.contact_id == contact_id,
        )
        if meta_account_id:
            query = query.filter(self.model_class.meta_account_id == meta_account_id)
        else:
            query = query.filter(self.model_class.meta_account_id.is_(None))
        return query.first()

    def get_or_create(self, workspace_id: str, contact_id: str, meta_account_id: Optional[str] = None) -> Conversation:
        existing = self.get_by_workspace_and_contact(workspace_id, contact_id, meta_account_id)
        if existing:
            return existing
        conversation = Conversation(
            workspace_id=workspace_id,
            contact_id=contact_id,
            meta_account_id=meta_account_id,
            status="OPEN",
            priority="NORMAL",
            unread_count=0,
        )
        self.session.add(conversation)
        self.session.commit()
        self.session.refresh(conversation)
        return conversation

    def touch_with_message(self, conversation_id: str, preview: str, message_ts, increment_unread: bool = False) -> Optional[Conversation]:
        conversation = self.get_by_id(conversation_id)
        if not conversation:
            return None
        conversation.last_message_at = message_ts
        conversation.last_message_preview = (preview or "")[:255]
        if increment_unread:
            conversation.unread_count = (conversation.unread_count or 0) + 1
        self.session.commit()
        self.session.refresh(conversation)
        return conversation

    def mark_read(self, conversation_id: str) -> bool:
        conversation = self.get_by_id(conversation_id)
        if not conversation:
            return False
        conversation.unread_count = 0
        self.session.commit()
        return True

    def set_archived(self, conversation_id: str, archived: bool) -> bool:
        conversation = self.get_by_id(conversation_id)
        if not conversation:
            return False
        conversation.is_archived = archived
        self.session.commit()
        return True

    def set_pinned(self, conversation_id: str, pinned: bool) -> bool:
        conversation = self.get_by_id(conversation_id)
        if not conversation:
            return False
        conversation.is_pinned = pinned
        self.session.commit()
        return True

    def set_muted(self, conversation_id: str, muted: bool) -> bool:
        conversation = self.get_by_id(conversation_id)
        if not conversation:
            return False
        conversation.is_muted = muted
        self.session.commit()
        return True

    def set_deleted(self, conversation_id: str, deleted: bool) -> bool:
        conversation = self.get_by_id(conversation_id)
        if not conversation:
            return False
        conversation.is_deleted = deleted
        self.session.commit()
        return True
