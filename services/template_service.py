import logging
from typing import List, Optional
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from core.models.template import Template
from core.models.meta_account import MetaAccount
from services.meta_cloud_service import MetaCloudService, TemplateDTO

logger = logging.getLogger(__name__)

class TemplateService:
    def __init__(self, db: Session):
        self.db = db
        self.meta_service = MetaCloudService()

    def sync_templates(self, workspace_id: str, meta_account_id: str) -> bool:
        """
        Fetches templates from Meta for a specific account and updates local DB.
        """
        try:
            account = self.db.query(MetaAccount).filter(
                MetaAccount.id == meta_account_id,
                MetaAccount.workspace_id == workspace_id
            ).first()
            
            if not account:
                logger.error(f"Meta Account {meta_account_id} not found for workspace {workspace_id}")
                return False
                
            templates_dto, error = self.meta_service.get_message_templates(
                account.waba_id, 
                account.access_token
            )
            
            if error:
                logger.error(f"Failed to fetch templates from Meta: {error}")
                return False
                
            # Update or create templates in local DB
            for dto in templates_dto:
                self._upsert_template(workspace_id, meta_account_id, dto)
                
            # Cleanup deleted templates (optional but recommended)
            # self._prune_deleted_templates(workspace_id, meta_account_id, templates_dto)
            
            self.db.commit()
            return True
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error syncing templates: {e}")
            return False

    def _upsert_template(self, workspace_id: str, meta_account_id: str, dto: TemplateDTO):
        """Helper to create or update a template record."""
        # Convert components to JSON-serializable format
        components_data = [
            {"type": c.type, "text": c.text, "format": c.format} 
            for c in dto.components
        ]
        
        template = self.db.query(Template).filter(Template.id == dto.id).first()
        if not template:
            template = Template(
                id=dto.id,
                workspace_id=workspace_id,
                meta_account_id=meta_account_id
            )
            self.db.add(template)
            
        template.name = dto.name
        template.status = dto.status
        template.category = dto.category
        template.language = dto.language
        template.components_json = components_data
        template.updated_at = datetime.now(timezone.utc)

    def get_templates(self, workspace_id: str, meta_account_id: Optional[str] = None) -> List[Template]:
        """Returns cached templates for a workspace."""
        query = self.db.query(Template).filter(Template.workspace_id == workspace_id)
        if meta_account_id:
            query = query.filter(Template.meta_account_id == meta_account_id)
        return query.all()
