from typing import List, Optional
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))) # Explicitly add project root to sys.path
from dataclasses import dataclass
from sqlalchemy.orm import Session
import logging

from core.repositories.workspace_repository import WorkspaceRepository
from core.models.workspace import Workspace, WorkspaceMember, WorkspaceRole
from core.models.user import User # Needed for owner relationship

logger = logging.getLogger(__name__)

@dataclass
class WorkspaceDTO:
    id: str
    name: str
    owner_id: str
    role: str # Role of the current user in this workspace

@dataclass
class WorkspaceAnalyticsDTO:
    total_users: int
    total_messages: int
    sync_health: str # e.g., "95%"
    total_messages_sent: int = 0
    total_messages_received: int = 0
    active_conversations: int = 0
    new_contacts: int = 0

@dataclass
class WorkspaceMemberDTO:
    id: str
    username: str
    email: str
    role: str
    is_external_customer: bool = False

class WorkspaceService:
    def __init__(self, session: Session):
        self.repository = WorkspaceRepository(session)

    def get_user_workspaces(self, user_id: str) -> List[WorkspaceDTO]:
        memberships = self.repository.get_memberships_by_user_id(user_id)
        workspaces = []
        for membership in memberships:
            workspaces.append(WorkspaceDTO(
                id=membership.workspace.id,
                name=membership.workspace.name,
                owner_id=membership.workspace.owner_id,
                role=membership.role.value
            ))
        return workspaces

    def create_default_workspace(self, user_id: str, username: str) -> WorkspaceDTO:
        workspace_name = f"{username}'s Workspace"
        workspace = Workspace(name=workspace_name, owner_id=user_id)
        self.repository.add(workspace) # Adds and commits workspace

        # Add the user as an admin to their own workspace
        member = WorkspaceMember(workspace_id=workspace.id, user_id=user_id, role=WorkspaceRole.ADMIN)
        self.repository.add_member(member) # Adds and commits member
        
        logger.info(f"Default workspace '{workspace_name}' created for user {username}")
        return WorkspaceDTO(
            id=workspace.id,
            name=workspace.name,
            owner_id=workspace.owner_id,
            role=WorkspaceRole.ADMIN.value
        )

    def get_workspace_analytics(self, workspace_id: str) -> WorkspaceAnalyticsDTO:
        stats = self.repository.get_workspace_stats(workspace_id)
        
        total_messages = stats.get("messages", 0)
        synced_messages = stats.get("synced", 0)
        
        sync_health = "100%"
        if total_messages > 0:
            sync_health = f"{int((synced_messages / total_messages) * 100)}%"

        return WorkspaceAnalyticsDTO(
            total_users=stats.get("users", 0),
            total_messages=total_messages,
            sync_health=sync_health,
            total_messages_sent=stats.get("messages_sent", 0),
            total_messages_received=stats.get("messages_received", 0),
            active_conversations=stats.get("active_conversations", 0),
            new_contacts=stats.get("new_contacts", 0),
        )

    def get_workspace_members(self, workspace_id: str) -> List[WorkspaceMemberDTO]:
        members = self.repository.get_members_by_workspace_id(workspace_id)
        member_dtos = []
        for member in members:
            is_external = member.user.email.endswith("@wa.external") # Heuristic for external WA users
            member_dtos.append(WorkspaceMemberDTO(
                id=member.user.id,
                username=member.user.username,
                email=member.user.email,
                role=member.role.value,
                is_external_customer=is_external
            ))
        return member_dtos
