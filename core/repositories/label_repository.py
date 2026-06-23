from typing import List, Optional

from sqlalchemy.orm import Session

from core.models.contact import Contact
from core.models.conversation import Conversation
from core.models.label import Label
from core.repository import BaseRepository


class LabelRepository(BaseRepository[Label]):
    def __init__(self, session: Session):
        super().__init__(session, Label)

    def get_by_workspace(self, workspace_id: str) -> List[Label]:
        return self.session.query(self.model_class).filter(self.model_class.workspace_id == workspace_id).order_by(self.model_class.name.asc()).all()

    def get_by_name(self, workspace_id: str, name: str) -> Optional[Label]:
        return (
            self.session.query(self.model_class)
            .filter(self.model_class.workspace_id == workspace_id, self.model_class.name == name)
            .first()
        )

    def attach_to_contact(self, label_id: str, contact_id: str) -> bool:
        label = self.get_by_id(label_id)
        contact = self.session.query(Contact).filter(Contact.id == contact_id).first()
        if not label or not contact:
            return False
        if label not in contact.labels:
            contact.labels.append(label)
            self.session.commit()
        return True

    def detach_from_contact(self, label_id: str, contact_id: str) -> bool:
        label = self.get_by_id(label_id)
        contact = self.session.query(Contact).filter(Contact.id == contact_id).first()
        if not label or not contact:
            return False
        if label in contact.labels:
            contact.labels.remove(label)
            self.session.commit()
        return True

    def attach_to_conversation(self, label_id: str, conversation_id: str) -> bool:
        label = self.get_by_id(label_id)
        conversation = self.session.query(Conversation).filter(Conversation.id == conversation_id).first()
        if not label or not conversation:
            return False
        if label not in conversation.labels:
            conversation.labels.append(label)
            self.session.commit()
        return True

    def detach_from_conversation(self, label_id: str, conversation_id: str) -> bool:
        label = self.get_by_id(label_id)
        conversation = self.session.query(Conversation).filter(Conversation.id == conversation_id).first()
        if not label or not conversation:
            return False
        if label in conversation.labels:
            conversation.labels.remove(label)
            self.session.commit()
        return True
