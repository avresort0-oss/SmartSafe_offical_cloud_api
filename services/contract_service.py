import os
import shutil
import uuid
from dataclasses import dataclass
from datetime import date
from typing import List, Optional

from sqlalchemy.orm import Session

from core.models.contract import Contract
from core.repositories.contract_repository import ContractRepository


VALID_TRANSITIONS = {
    "DRAFT": {"ACTIVE", "CANCELLED"},
    "ACTIVE": {"PAUSED", "EXPIRED", "CANCELLED"},
    "PAUSED": {"ACTIVE", "CANCELLED"},
    "EXPIRED": set(),
    "CANCELLED": set(),
}


@dataclass
class ContractDTO:
    id: str
    workspace_id: str
    contact_id: str
    title: str
    contract_number: Optional[str]
    contract_type: Optional[str]
    status: str
    value_amount: Optional[float]
    currency: str
    start_date: Optional[str]
    end_date: Optional[str]
    renewal_date: Optional[str]
    reminder_days_before: int
    document_path: Optional[str]
    owner_user_id: Optional[str]
    notes: str


@dataclass
class ContractCreateDTO:
    workspace_id: str
    contact_id: str
    title: str
    contract_number: Optional[str] = None
    contract_type: Optional[str] = "SERVICE"
    status: str = "DRAFT"
    value_amount: Optional[float] = None
    currency: str = "USD"
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    renewal_date: Optional[date] = None
    reminder_days_before: int = 30
    document_path: Optional[str] = None
    owner_user_id: Optional[str] = None
    notes: str = ""


class ContractService:
    def __init__(self, session: Session):
        self.repository = ContractRepository(session)
        self.session = session

    def _to_dto(self, c: Contract) -> ContractDTO:
        return ContractDTO(
            id=c.id,
            workspace_id=c.workspace_id,
            contact_id=c.contact_id,
            title=c.title,
            contract_number=c.contract_number,
            contract_type=c.contract_type,
            status=c.status,
            value_amount=c.value_amount,
            currency=c.currency,
            start_date=c.start_date.isoformat() if c.start_date else None,
            end_date=c.end_date.isoformat() if c.end_date else None,
            renewal_date=c.renewal_date.isoformat() if c.renewal_date else None,
            reminder_days_before=c.reminder_days_before,
            document_path=c.document_path,
            owner_user_id=c.owner_user_id,
            notes=c.notes or "",
        )

    def _copy_contract_file(self, src_path: Optional[str]) -> Optional[str]:
        if not src_path or not os.path.exists(src_path) or not os.path.isfile(src_path):
            return None
        contracts_dir = os.path.join(os.getcwd(), "attachments", "contracts")
        os.makedirs(contracts_dir, exist_ok=True)
        safe_name = f"{uuid.uuid4().hex[:8]}_{os.path.basename(src_path)}"
        dst_path = os.path.join(contracts_dir, safe_name)
        shutil.copy2(src_path, dst_path)
        return dst_path

    def list_contracts(self, workspace_id: str) -> List[ContractDTO]:
        return [self._to_dto(c) for c in self.repository.get_by_workspace(workspace_id)]

    def create_contract(self, dto: ContractCreateDTO) -> ContractDTO:
        stored_doc = self._copy_contract_file(dto.document_path)
        contract = Contract(
            workspace_id=dto.workspace_id,
            contact_id=dto.contact_id,
            title=dto.title.strip(),
            contract_number=dto.contract_number,
            contract_type=dto.contract_type,
            status=dto.status,
            value_amount=dto.value_amount,
            currency=dto.currency or "USD",
            start_date=dto.start_date,
            end_date=dto.end_date,
            renewal_date=dto.renewal_date,
            reminder_days_before=dto.reminder_days_before,
            document_path=stored_doc,
            owner_user_id=dto.owner_user_id,
            notes=dto.notes or "",
        )
        saved = self.repository.add(contract)
        return self._to_dto(saved)

    def update_status(self, contract_id: str, new_status: str) -> Optional[ContractDTO]:
        contract = self.repository.get_by_id(contract_id)
        if not contract:
            return None
        allowed = VALID_TRANSITIONS.get(contract.status, set())
        if new_status not in allowed and new_status != contract.status:
            raise ValueError(f"Invalid status transition: {contract.status} -> {new_status}")
        updated = self.repository.update_status(contract_id, new_status)
        return self._to_dto(updated) if updated else None
