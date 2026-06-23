import logging
from typing import List, Optional, Any
from dataclasses import dataclass
from core.database import SessionLocal
from core.repositories.auto_reply_repository import AutoReplyRepository
from core.models.auto_reply_rule import AutoReplyRule

logger = logging.getLogger(__name__)

@dataclass
class AutoReplyRuleDTO:
    id: str
    trigger_keyword: str
    trigger_type: str
    response_text: str
    attachment_path: Optional[str]
    is_active: bool

class AutoReplyService:
    def __init__(self):
        pass

    def _to_dto(self, rule: AutoReplyRule) -> AutoReplyRuleDTO:
        return AutoReplyRuleDTO(
            id=rule.id,
            trigger_keyword=rule.trigger_keyword,
            trigger_type=rule.trigger_type,
            response_text=rule.response_text,
            attachment_path=rule.attachment_path,
            is_active=rule.is_active
        )

    def get_rules(self, workspace_id: str) -> List[AutoReplyRuleDTO]:
        with SessionLocal() as session:
            repo = AutoReplyRepository(session)
            rules = repo.get_all_by_workspace(workspace_id)
            return [self._to_dto(r) for r in rules]

    def create_rule(self, workspace_id: str, trigger: str, response: str, trigger_type: str = "exact", attachment: str = None) -> AutoReplyRuleDTO:
        with SessionLocal() as session:
            repo = AutoReplyRepository(session)
            rule = AutoReplyRule(
                workspace_id=workspace_id,
                trigger_keyword=trigger,
                response_text=response,
                trigger_type=trigger_type,
                attachment_path=attachment
            )
            saved = repo.add(rule)
            return self._to_dto(saved)

    def delete_rule(self, rule_id: str) -> bool:
        with SessionLocal() as session:
            repo = AutoReplyRepository(session)
            return repo.delete(rule_id)

    def toggle_rule(self, rule_id: str) -> bool:
        with SessionLocal() as session:
            repo = AutoReplyRepository(session)
            rule = repo.get_by_id(rule_id)
            if rule:
                repo.update(rule_id, is_active=not rule.is_active)
                return True
            return False

    def process_incoming_message(self, workspace_id: str, content: str) -> Optional[dict]:
        """Matches incoming content against active rules and returns a response payload if matched."""
        with SessionLocal() as session:
            repo = AutoReplyRepository(session)
            rules = repo.get_active_by_workspace(workspace_id)
            
            content_lower = content.lower().strip()
            
            for rule in rules:
                trigger_lower = rule.trigger_keyword.lower().strip()
                match = False
                
                if rule.trigger_type == "exact":
                    match = content_lower == trigger_lower
                elif rule.trigger_type == "contains":
                    match = trigger_lower in content_lower
                elif rule.trigger_type == "starts_with":
                    match = content_lower.startswith(trigger_lower)
                
                if match:
                    logger.info(f"Auto-reply triggered for rule: {rule.trigger_keyword}")
                    return {
                        "content": rule.response_text,
                        "attachment_path": rule.attachment_path
                    }
            return None
