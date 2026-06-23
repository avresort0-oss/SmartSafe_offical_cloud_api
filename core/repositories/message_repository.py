from datetime import datetime
from typing import List, Optional
import sys
import os
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, project_root) # Explicitly add project root to sys.path
from sqlalchemy.orm import Session, joinedload

from core.repository import BaseRepository
from core.models.message import Message


class MessageRepository(BaseRepository[Message]):
    """
    Concrete repository for the Message entity.
    """
    def __init__(self, session: Session):
        super().__init__(session, Message)

    def get_recent_messages(
        self,
        workspace_id: str,
        limit: int = 100,
        since_timestamp: Optional[datetime] = None,
        conversation_id: Optional[str] = None,
    ) -> List[Message]:
        """Fetches recent messages, eager-loading the sender to prevent N+1 queries."""
        query = self.session.query(self.model_class).options(joinedload(self.model_class.sender)).filter(
            self.model_class.workspace_id == workspace_id,
            self.model_class.is_deleted == False
        )
        if conversation_id:
            query = query.filter(self.model_class.conversation_id == conversation_id)
        if since_timestamp:
            # Use updated_at so sync/star changes are also captured incrementally.
            query = query.filter(self.model_class.updated_at > since_timestamp)
            return query.order_by(self.model_class.created_at.asc()).limit(limit).all()

        # Initial history load: fetch latest messages, then re-sort ascending for chat display.
        rows = query.order_by(self.model_class.created_at.desc()).limit(limit).all()
        return list(reversed(rows))

    def get_all_active_messages(self, limit: int = 500) -> List[Message]:
        """Fetches global active messages across all workspaces for in-memory decryption search."""
        return self.session.query(self.model_class).options(joinedload(self.model_class.sender))\
            .filter(self.model_class.is_deleted == False).order_by(self.model_class.created_at.desc()).limit(limit).all()

    def get_unsynced_messages(self, limit: int = 50) -> List[Message]:
        """Fetches a batch of non-deleted messages that have not yet been pushed to the cloud."""
        return self.session.query(self.model_class).filter(self.model_class.is_synced == False, self.model_class.is_deleted == False).limit(limit).all()

    def mark_as_synced(self, message_ids: List[str]) -> None:
        """Bulk updates the sync status of successfully transmitted messages."""
        self.session.query(self.model_class).filter(self.model_class.id.in_(message_ids)).update({"is_synced": True}, synchronize_session=False)
        self.session.commit()

    def soft_delete(self, message_id: str) -> bool:
        """Marks a message as deleted so the sync engine can propagate the deletion."""
        result = self.session.query(self.model_class).filter(self.model_class.id == message_id).update({"is_deleted": True, "is_synced": False}, synchronize_session=False)
        self.session.commit()
        return result > 0

    def get_unsynced_deletions(self, limit: int = 50) -> List[Message]:
        return self.session.query(self.model_class).filter(self.model_class.is_deleted == True, self.model_class.is_synced == False).limit(limit).all()

    def hard_delete_synced_deletions(self, message_ids: List[str]) -> None:
        """Permanently removes deleted messages from the local SQLite store once confirmed by the cloud."""
        self.session.query(self.model_class).filter(self.model_class.id.in_(message_ids)).delete(synchronize_session=False)
        self.session.commit()

    def list_starred_by_workspace(self, workspace_id: str, limit: int = 200) -> List[Message]:
        """Fetches starred, non-deleted messages across all conversations in a workspace."""
        return (
            self.session.query(self.model_class)
            .options(joinedload(self.model_class.contact))
            .filter(
                self.model_class.workspace_id == workspace_id,
                self.model_class.is_starred == True,
                self.model_class.is_deleted == False,
            )
            .order_by(self.model_class.created_at.desc())
            .limit(limit)
            .all()
        )

    def toggle_star(self, message_id: str) -> bool:
        """Toggles the starred status of a message and returns the new state."""
        msg = self.get_by_id(message_id)
        if msg:
            msg.is_starred = not msg.is_starred
            self.session.commit()
            return msg.is_starred
        return False
