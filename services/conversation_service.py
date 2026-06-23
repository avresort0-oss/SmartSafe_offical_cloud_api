from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional

from sqlalchemy.orm import Session

from core.models.conversation import Conversation
from core.repositories.conversation_repository import ConversationRepository


@dataclass
class ConversationDTO:
    id: str
    workspace_id: str
    contact_id: str
    meta_account_id: Optional[str]
    status: str
    priority: str
    assigned_user_id: Optional[str]
    last_message_at: Optional[str]
    last_message_preview: str
    unread_count: int
    contact_name: str
    contact_phone: str
    labels: List[str] = field(default_factory=list)
    is_archived: bool = False
    is_pinned: bool = False
    is_muted: bool = False


@dataclass
class ConversationListItemDTO:
    id: str
    contact_name: str
    contact_phone: str
    last_message_preview: str
    last_message_at: Optional[str]
    unread_count: int
    status: str
    assigned_user_id: Optional[str]
    labels: List[str] = field(default_factory=list)
    is_archived: bool = False
    is_pinned: bool = False
    is_muted: bool = False


class ConversationService:
    def __init__(self, session: Session):
        self.repository = ConversationRepository(session)
        self.session = session

    def _collect_labels(self, conv: Conversation) -> List[str]:
        names = {label.name for label in getattr(conv, "labels", [])}
        if conv.contact:
            names.update(label.name for label in getattr(conv.contact, "labels", []))
        return sorted(names)

    def _to_dto(self, conv: Conversation) -> ConversationDTO:
        return ConversationDTO(
            id=conv.id,
            workspace_id=conv.workspace_id,
            contact_id=conv.contact_id,
            meta_account_id=conv.meta_account_id,
            status=conv.status,
            priority=conv.priority,
            assigned_user_id=conv.assigned_user_id,
            last_message_at=conv.last_message_at.isoformat() if conv.last_message_at else None,
            last_message_preview=conv.last_message_preview or "",
            unread_count=conv.unread_count or 0,
            contact_name=conv.contact.display_name if conv.contact else "Unknown",
            contact_phone=conv.contact.phone_e164 if conv.contact else "",
            labels=self._collect_labels(conv),
            is_archived=bool(conv.is_archived),
            is_pinned=bool(conv.is_pinned),
            is_muted=bool(conv.is_muted),
        )

    def list_conversations(
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
    ) -> List[ConversationListItemDTO]:
        rows = self.repository.list_by_workspace(
            workspace_id=workspace_id,
            search=search,
            status=status,
            assigned_user_id=assigned_user_id,
            label_query=label_query,
            unread_only=unread_only,
            meta_account_id=meta_account_id,
            archived=archived,
            limit=limit,
            offset=offset,
        )
        items: List[ConversationListItemDTO] = []
        for conv in rows:
            items.append(
                ConversationListItemDTO(
                    id=conv.id,
                    contact_name=conv.contact.display_name if conv.contact else "Unknown",
                    contact_phone=conv.contact.phone_e164 if conv.contact else "",
                    last_message_preview=conv.last_message_preview or "",
                    last_message_at=conv.last_message_at.isoformat() if conv.last_message_at else None,
                    unread_count=conv.unread_count or 0,
                    status=conv.status,
                    assigned_user_id=conv.assigned_user_id,
                    labels=self._collect_labels(conv),
                    is_archived=bool(conv.is_archived),
                    is_pinned=bool(conv.is_pinned),
                    is_muted=bool(conv.is_muted),
                )
            )
        return items

    def get_or_create_conversation(self, workspace_id: str, contact_id: str, meta_account_id: Optional[str] = None) -> ConversationDTO:
        conv = self.repository.get_or_create(workspace_id, contact_id, meta_account_id)
        return self._to_dto(conv)

    def get_conversation(self, conversation_id: str) -> Optional[ConversationDTO]:
        conv = self.repository.get_by_id(conversation_id)
        return self._to_dto(conv) if conv else None

    def assign_conversation(self, conversation_id: str, user_id: Optional[str]) -> Optional[ConversationDTO]:
        conv = self.repository.get_by_id(conversation_id)
        if not conv:
            return None
        conv.assigned_user_id = user_id
        self.session.commit()
        self.session.refresh(conv)
        return self._to_dto(conv)

    def update_status(self, conversation_id: str, status: str) -> Optional[ConversationDTO]:
        conv = self.repository.get_by_id(conversation_id)
        if not conv:
            return None
        conv.status = status
        self.session.commit()
        self.session.refresh(conv)
        return self._to_dto(conv)

    def mark_read(self, conversation_id: str) -> bool:
        return self.repository.mark_read(conversation_id)

    def archive_conversation(self, conversation_id: str) -> Optional[ConversationDTO]:
        if not self.repository.set_archived(conversation_id, True):
            return None
        conv = self.repository.get_by_id(conversation_id)
        return self._to_dto(conv) if conv else None

    def unarchive_conversation(self, conversation_id: str) -> Optional[ConversationDTO]:
        if not self.repository.set_archived(conversation_id, False):
            return None
        conv = self.repository.get_by_id(conversation_id)
        return self._to_dto(conv) if conv else None

    def pin_conversation(self, conversation_id: str) -> Optional[ConversationDTO]:
        if not self.repository.set_pinned(conversation_id, True):
            return None
        conv = self.repository.get_by_id(conversation_id)
        return self._to_dto(conv) if conv else None

    def unpin_conversation(self, conversation_id: str) -> Optional[ConversationDTO]:
        if not self.repository.set_pinned(conversation_id, False):
            return None
        conv = self.repository.get_by_id(conversation_id)
        return self._to_dto(conv) if conv else None

    def mute_conversation(self, conversation_id: str) -> Optional[ConversationDTO]:
        if not self.repository.set_muted(conversation_id, True):
            return None
        conv = self.repository.get_by_id(conversation_id)
        return self._to_dto(conv) if conv else None

    def unmute_conversation(self, conversation_id: str) -> Optional[ConversationDTO]:
        if not self.repository.set_muted(conversation_id, False):
            return None
        conv = self.repository.get_by_id(conversation_id)
        return self._to_dto(conv) if conv else None

    def delete_conversation(self, conversation_id: str) -> bool:
        return self.repository.set_deleted(conversation_id, True)

    def update_on_new_message(self, conversation_id: str, preview: str, message_ts: datetime, inbound: bool) -> Optional[ConversationDTO]:
        conv = self.repository.touch_with_message(
            conversation_id=conversation_id,
            preview=preview,
            message_ts=message_ts,
            increment_unread=inbound,
        )
        return self._to_dto(conv) if conv else None
