import bcrypt
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))) # Explicitly add project root to sys.path
from typing import Optional
from dataclasses import dataclass
from sqlalchemy.orm import Session
import logging

from core.repositories.user_repository import UserRepository
from core.models.user import User

logger = logging.getLogger(__name__)

@dataclass
class UserCreateDTO:
    username: str
    email: str
    password: str

@dataclass
class UserResponseDTO:
    id: str
    username: str
    email: str
    is_active: bool

class UserService:
    def __init__(self, session: Session):
        self.repository = UserRepository(session)

    def _hash_password(self, password: str) -> str:
        hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
        return hashed.decode('utf-8')

    def _check_password(self, password: str, hashed_password: str) -> bool:
        if not hashed_password:
            return False
        try:
            return bcrypt.checkpw(password.encode('utf-8'), hashed_password.encode('utf-8'))
        except (ValueError, TypeError):
            logger.warning("Invalid password hash format encountered for user authentication.")
            return False

    def register_user(self, dto: UserCreateDTO) -> UserResponseDTO:
        if self.repository.get_by_email(dto.email) or self.repository.get_by_username(dto.username):
            raise ValueError("A user with this email or username already exists.")

        hashed_password = self._hash_password(dto.password)
        user = User(username=dto.username, email=dto.email, password_hash=hashed_password)
        saved_user = self.repository.add(user)
        logger.info(f"User registered: {saved_user.username}")
        return UserResponseDTO(
            id=saved_user.id,
            username=saved_user.username,
            email=saved_user.email,
            is_active=saved_user.is_active
        )

    def authenticate_user(self, username: str, password: str) -> Optional[UserResponseDTO]:
        user = self.repository.get_by_username(username)
        if user and self._check_password(password, user.password_hash):
            logger.info(f"User authenticated: {user.username}")
            return UserResponseDTO(
                id=user.id,
                username=user.username,
                email=user.email,
                is_active=user.is_active
            )
        logger.warning(f"Authentication failed for username: {username}")
        return None

    def get_user_by_id(self, user_id: str) -> Optional[UserResponseDTO]:
        user = self.repository.get_by_id(user_id)
        if user:
            return UserResponseDTO(id=user.id, username=user.username, email=user.email, is_active=user.is_active)
        return None
