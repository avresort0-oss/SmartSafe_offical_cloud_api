from sqlalchemy.orm import Session
from typing import List, Optional
from ..models.auto_reply_rule import AutoReplyRule

class AutoReplyRepository:
    def __init__(self, session: Session):
        self.session = session

    def add(self, rule: AutoReplyRule) -> AutoReplyRule:
        self.session.add(rule)
        self.session.commit()
        self.session.refresh(rule)
        return rule

    def get_all_by_workspace(self, workspace_id: str) -> List[AutoReplyRule]:
        return self.session.query(AutoReplyRule).filter_by(workspace_id=workspace_id).all()

    def get_active_by_workspace(self, workspace_id: str) -> List[AutoReplyRule]:
        return self.session.query(AutoReplyRule).filter_by(workspace_id=workspace_id, is_active=True).all()

    def get_by_id(self, rule_id: str) -> Optional[AutoReplyRule]:
        return self.session.query(AutoReplyRule).filter_by(id=rule_id).first()

    def delete(self, rule_id: str) -> bool:
        rule = self.get_by_id(rule_id)
        if rule:
            self.session.delete(rule)
            self.session.commit()
            return True
        return False

    def update(self, rule_id: str, **kwargs) -> Optional[AutoReplyRule]:
        rule = self.get_by_id(rule_id)
        if rule:
            for key, value in kwargs.items():
                if hasattr(rule, key):
                    setattr(rule, key, value)
            self.session.commit()
            self.session.refresh(rule)
            return rule
        return None
