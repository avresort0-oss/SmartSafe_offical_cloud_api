from typing import Optional
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))) # Explicitly add project root to sys.path
from sqlalchemy.orm import Session

from core.repository import BaseRepository
from core.models.user import User

class UserRepository(BaseRepository[User]):
    """
    Concrete repository for the User entity.
    """
    def __init__(self, session: Session):
        super().__init__(session, User)

    def get_by_email(self, email: str) -> Optional[User]:
        """Fetches a user by their email address."""
        return self.session.query(self.model_class).filter_by(email=email).first()

    def get_by_username(self, username: str) -> Optional[User]:
        """Fetches a user by their username."""
        return self.session.query(self.model_class).filter_by(username=username).first()

    def get_active_users(self) -> list[User]:
        """Fetches all active users."""
        return self.session.query(self.model_class).filter_by(is_active=True).all()