from typing import Optional
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))) # Explicitly add project root to sys.path
import logging

from services.user_service import UserResponseDTO
from services.workspace_service import WorkspaceDTO

logger = logging.getLogger(__name__)

class AppStateManager:
    """
    Manages the global application state, such as the current authenticated user
    and the active workspace. This is a singleton to ensure consistent state.
    """
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(AppStateManager, cls).__new__(cls)
            cls._instance._current_user: Optional[UserResponseDTO] = None
            cls._instance._current_workspace: Optional[WorkspaceDTO] = None
        return cls._instance

    def set_current_user(self, user: UserResponseDTO):
        self._current_user = user
        logger.info(f"Current user set: {user.username}")

    def get_current_user(self) -> Optional[UserResponseDTO]:
        return self._current_user

    def set_current_workspace(self, workspace: WorkspaceDTO):
        self._current_workspace = workspace
        logger.info(f"Current workspace set: {workspace.name}")

    def get_current_workspace(self) -> Optional[WorkspaceDTO]:
        return self._current_workspace

    def logout(self):
        self._current_user = None
        self._current_workspace = None
        logger.info("User logged out. Application state cleared.")

# Export a singleton instance
app_state_manager = AppStateManager()