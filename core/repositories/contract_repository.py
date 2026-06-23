from datetime import date
from typing import List, Optional

from sqlalchemy.orm import Session, joinedload

from core.models.contract import Contract
from core.repository import BaseRepository


class ContractRepository(BaseRepository[Contract]):
    def __init__(self, session: Session):
        super().__init__(session, Contract)

    def get_by_workspace(self, workspace_id: str) -> List[Contract]:
        return (
            self.session.query(self.model_class)
            .options(joinedload(self.model_class.contact), joinedload(self.model_class.owner))
            .filter(self.model_class.workspace_id == workspace_id)
            .order_by(self.model_class.updated_at.desc())
            .all()
        )

    def update_status(self, contract_id: str, status: str) -> Optional[Contract]:
        contract = self.get_by_id(contract_id)
        if not contract:
            return None
        contract.status = status
        self.session.commit()
        self.session.refresh(contract)
        return contract

    def due_for_renewal(self, workspace_id: str, today: date, max_days: int = 30) -> List[Contract]:
        from datetime import timedelta

        horizon = today + timedelta(days=max_days)
        return (
            self.session.query(self.model_class)
            .filter(
                self.model_class.workspace_id == workspace_id,
                self.model_class.renewal_date.isnot(None),
                self.model_class.renewal_date >= today,
                self.model_class.renewal_date <= horizon,
            )
            .all()
        )
