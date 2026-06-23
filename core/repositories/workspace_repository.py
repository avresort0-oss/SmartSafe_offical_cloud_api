from typing import List, Optional
import sys
import os
from datetime import datetime, timedelta, timezone
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))) # Explicitly add project root to sys.path
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func

from core.repository import BaseRepository
from core.models.workspace import Workspace, WorkspaceMember
from core.models.contact import Contact
from core.models.conversation import Conversation
from core.models.message import Message

class WorkspaceRepository(BaseRepository[Workspace]):
    """
    Concrete repository for the Workspace entity.
    """
    def __init__(self, session: Session):
        super().__init__(session, Workspace)
        self.session = session # Keep session for direct queries

    def get_memberships_by_user_id(self, user_id: str) -> List[WorkspaceMember]:
        """Fetches all workspace memberships for a given user."""
        return self.session.query(WorkspaceMember).options(joinedload(WorkspaceMember.workspace))\
            .filter(WorkspaceMember.user_id == user_id).all()

    def add_member(self, member: WorkspaceMember) -> WorkspaceMember:
        """Adds a new member to a workspace."""
        self.session.add(member)
        self.session.commit()
        self.session.refresh(member)
        return member

    def get_workspace_stats(self, workspace_id: str) -> dict:
        """Calculates basic analytics for a given workspace."""
        total_users = self.session.query(func.count(WorkspaceMember.user_id)).filter(WorkspaceMember.workspace_id == workspace_id).scalar()
        total_messages = self.session.query(func.count(Message.id)).filter(Message.workspace_id == workspace_id).scalar()
        synced_messages = self.session.query(func.count(Message.id)).filter(Message.workspace_id == workspace_id, Message.is_synced == True).scalar()
        total_messages_sent = self.session.query(func.count(Message.id)).filter(
            Message.workspace_id == workspace_id,
            Message.direction == "OUTBOUND",
            Message.is_deleted == False,
        ).scalar()
        total_messages_received = self.session.query(func.count(Message.id)).filter(
            Message.workspace_id == workspace_id,
            Message.direction == "INBOUND",
            Message.is_deleted == False,
        ).scalar()
        active_conversations = self.session.query(func.count(Conversation.id)).filter(
            Conversation.workspace_id == workspace_id,
            Conversation.status.in_(["OPEN", "PENDING"]),
        ).scalar()
        seven_days_ago = datetime.now(timezone.utc) - timedelta(days=7)
        new_contacts = self.session.query(func.count(Contact.id)).filter(
            Contact.workspace_id == workspace_id,
            Contact.created_at >= seven_days_ago,
        ).scalar()

        return {
            "users": total_users or 0,
            "messages": total_messages or 0,
            "synced": synced_messages or 0,
            "messages_sent": total_messages_sent or 0,
            "messages_received": total_messages_received or 0,
            "active_conversations": active_conversations or 0,
            "new_contacts": new_contacts or 0,
        }

    def get_members_by_workspace_id(self, workspace_id: str) -> List[WorkspaceMember]:
        """Fetches all members of a specific workspace, eager-loading user details."""
        return self.session.query(WorkspaceMember).options(joinedload(WorkspaceMember.user))\
            .filter(WorkspaceMember.workspace_id == workspace_id).all()
