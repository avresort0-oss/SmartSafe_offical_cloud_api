from dataclasses import dataclass
from typing import List, Optional

from sqlalchemy.orm import Session

from core.models.label import Label
from core.repositories.label_repository import LabelRepository


@dataclass
class LabelDTO:
    id: str
    workspace_id: str
    name: str
    color_hex: str
    applies_to: str


class LabelService:
    def __init__(self, session: Session):
        self.repository = LabelRepository(session)

    def _to_dto(self, label: Label) -> LabelDTO:
        return LabelDTO(
            id=label.id,
            workspace_id=label.workspace_id,
            name=label.name,
            color_hex=label.color_hex,
            applies_to=label.applies_to,
        )

    def list_labels(self, workspace_id: str) -> List[LabelDTO]:
        return [self._to_dto(l) for l in self.repository.get_by_workspace(workspace_id)]

    def create_label(self, workspace_id: str, name: str, color_hex: str = "#00a884", applies_to: str = "BOTH") -> LabelDTO:
        existing = self.repository.get_by_name(workspace_id, name)
        if existing:
            return self._to_dto(existing)
        entity = Label(workspace_id=workspace_id, name=name.strip(), color_hex=color_hex, applies_to=applies_to)
        saved = self.repository.add(entity)
        return self._to_dto(saved)

    def attach_to_contact(self, label_id: str, contact_id: str) -> bool:
        return self.repository.attach_to_contact(label_id, contact_id)

    def detach_from_contact(self, label_id: str, contact_id: str) -> bool:
        return self.repository.detach_from_contact(label_id, contact_id)

    def attach_to_conversation(self, label_id: str, conversation_id: str) -> bool:
        return self.repository.attach_to_conversation(label_id, conversation_id)

    def detach_from_conversation(self, label_id: str, conversation_id: str) -> bool:
        return self.repository.detach_from_conversation(label_id, conversation_id)
