from typing import TypeVar, Generic, List, Optional
import sys
import os
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
import logging

logger = logging.getLogger(__name__)

T = TypeVar('T')

class BaseRepository(Generic[T]):
    """
    Generic base repository providing common CRUD operations for SQLAlchemy models.
    """
    def __init__(self, session: Session, model_class: type[T]):
        self.session = session
        self.model_class = model_class

    def add(self, entity: T) -> T:
        try:
            self.session.add(entity)
            self.session.commit()
            self.session.refresh(entity)
            return entity
        except SQLAlchemyError as e:
            self.session.rollback()
            logger.error(f"Error adding {self.model_class.__name__}: {e}", exc_info=True)
            raise

    def get_by_id(self, entity_id: str) -> Optional[T]:
        return self.session.query(self.model_class).filter_by(id=entity_id).first()

    def get_all(self) -> List[T]:
        return self.session.query(self.model_class).all()

    def delete(self, entity_id: str) -> bool:
        entity = self.get_by_id(entity_id)
        if entity:
            self.session.delete(entity)
            self.session.commit()
            return True
        return False