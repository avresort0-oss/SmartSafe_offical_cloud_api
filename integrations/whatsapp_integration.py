import logging
from typing import Optional

from sqlalchemy.orm import Session

from services.meta_cloud_service import MetaCloudService, MessageResultDTO
from services.meta_account_service import MetaAccountService, MetaAccountDTO

logger = logging.getLogger(__name__)

class WhatsAppIntegration:
    """
    High-level service to handle WhatsApp operations.
    It coordinates fetching credentials from the database and using the
    MetaCloudService to send messages.
    """
    def __init__(self, db_session: Session):
        self.db = db_session
        self.meta_cloud_service = MetaCloudService()
        self.meta_account_service = MetaAccountService(self.db, self.meta_cloud_service)

    def _get_active_credentials(self):
        """Fetches the active account credentials from the database."""
        from core.models.meta_account import MetaAccount
        # Fetch the first active account as a fallback for the dashboard stubs
        db_account = self.db.query(MetaAccount).filter(MetaAccount.is_active == True).first()
        if not db_account:
            logger.warning("[WhatsAppService] Meta account is not configured in the database.")
            return None
            
        return db_account

    def send_text_message(self, to_phone_number: str, text: str) -> MessageResultDTO:
        """
        Sends a plain-text message using configured credentials.
        """
        creds = self._get_active_credentials()
        if not creds:
            return MessageResultDTO(success=False, error="WhatsApp Integration is not configured.")

        logger.info(f"Sending message to {to_phone_number} using Phone ID {creds.phone_number_id}")
        
        result = self.meta_cloud_service.send_text_message(
            phone_number_id=creds.phone_number_id,
            access_token=creds.access_token,
            to_phone=to_phone_number,
            body=text
        )
        
        if result.success:
            logger.info(f"Successfully sent message. Message ID: {result.message_id}")
        else:
            logger.error(f"Failed to send message: {result.error}")
            
        return result

    def upload_media(self, file_path: str, mime_type: str) -> MessageResultDTO:
        creds = self._get_active_credentials()
        if not creds:
            return MessageResultDTO(success=False, error="WhatsApp Integration is not configured.")
        return self.meta_cloud_service.upload_media(
            phone_number_id=creds.phone_number_id,
            access_token=creds.access_token,
            file_path=file_path,
            mime_type=mime_type
        )

    def send_media_message(self, to_phone_number: str, media_id: str, media_type: str, caption: Optional[str] = None) -> MessageResultDTO:
        creds = self._get_active_credentials()
        if not creds:
            return MessageResultDTO(success=False, error="WhatsApp Integration is not configured.")
        return self.meta_cloud_service.send_media_message(
            phone_number_id=creds.phone_number_id,
            access_token=creds.access_token,
            to_phone=to_phone_number,
            media_id=media_id,
            media_type=media_type,
            caption=caption
        )

    def check_status(self) -> (bool, str):
        """
        Checks the status of the WhatsApp integration by fetching phone info.
        Returns a tuple of (is_valid: bool, message: str).
        """
        creds = self._get_active_credentials()
        if not creds:
            return False, "Not Configured: No Meta account found in the database."

        phone_info, error = self.meta_cloud_service.get_phone_info(
            phone_number_id=creds.phone_number_id,
            access_token=creds.access_token
        )

        if error:
            return False, f"API Error: {error}"
        
        if phone_info:
            return True, f"Connected: {phone_info.display_phone_number} (Quality: {phone_info.quality_rating})"
        
        return False, "Unknown error checking status."

    def send_message(self, to_phone_number: str, text: str) -> MessageResultDTO:
        """Alias for send_text_message to match MessageService call expectations."""
        return self.send_text_message(to_phone_number, text)

    def parse_webhook(self, payload: dict) -> list:
        """
        Parses an incoming Meta Webhook JSON payload.
        Returns a list of simplified message dicts: [{'from_phone': str, 'text': str, 'wamid': str}]
        """
        parsed_messages = []
        try:
            entries = payload.get("entry", [])
            for entry in entries:
                changes = entry.get("changes", [])
                for change in changes:
                    value = change.get("value", {})
                    metadata = value.get("metadata", {})
                    phone_number_id = metadata.get("phone_number_id")
                    messages = value.get("messages", [])
                    for msg in messages:
                        if msg.get("type") == "text":
                            parsed_messages.append({
                                "from_phone": msg.get("from"),
                                "text": msg.get("text", {}).get("body"),
                                "wamid": msg.get("id"),
                                "phone_number_id": phone_number_id,
                                "type": "text"
                            })
                        elif msg.get("type") in ["image", "video", "document", "audio"]:
                            media_dict = msg.get(msg.get("type"), {})
                            # If media has caption, use it as text fallback
                            parsed_messages.append({
                                "from_phone": msg.get("from"),
                                "text": media_dict.get("caption", f"[{msg.get('type').upper()} ATTACHMENT]"),
                                "wamid": msg.get("id"),
                                "phone_number_id": phone_number_id,
                                "type": msg.get("type"),
                                "media_id": media_dict.get("id")
                            })

                    statuses = value.get("statuses", [])
                    for status in statuses:
                        parsed_messages.append({
                            "type": "status",
                            "status": status.get("status"), # sent, delivered, read, failed
                            "wamid": status.get("id"),
                            "phone_number_id": phone_number_id,
                            "recipient_id": status.get("recipient_id")
                        })
        except Exception as e:
            logger.error(f"[WhatsAppIntegration] Error parsing webhook payload: {e}")
            
        return parsed_messages

    # You can add more methods here to wrap other meta_cloud_service functions
    # e.g., send_template_message, get_message_templates, etc.