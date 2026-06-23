import sys
import os
import logging
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)

logger = logging.getLogger(__name__)

# --- API Data Transfer Objects ---

@dataclass
class PhoneInfoDTO:
    """Represents the health and status of a WhatsApp Business phone number."""
    display_phone_number: str
    verified_name: str
    quality_rating: str
    api_status: str
    id: str

@dataclass
class TemplateComponentDTO:
    """Represents a component (header, body, footer, buttons) of a template."""
    type: str
    text: Optional[str] = None
    format: Optional[str] = None # for HEADER type (IMAGE, VIDEO, DOCUMENT)

@dataclass
class TemplateDTO:
    """Represents a single WhatsApp message template."""
    id: str
    name: str
    status: str
    category: str
    language: str
    components: List[TemplateComponentDTO] = field(default_factory=list)

@dataclass
class MessageResultDTO:
    """Represents the result of a message sending operation."""
    success: bool
    message_id: str = ""  # wamid from Meta API response
    error: str = ""


class MetaCloudService:
    """
    A pure service wrapper for the Meta Cloud (WhatsApp Business) API.
    This class handles all HTTP requests and does not interact with the database.
    """
    BASE_URL = "https://graph.facebook.com/v19.0"

    def __init__(self):
        self.session = self._create_session_with_retries()

    def _create_session_with_retries(self) -> requests.Session:
        """Configures a requests session with automatic retries for robustness."""
        session = requests.Session()
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "POST", "OPTIONS"]
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("https://", adapter)
        return session

    def _make_request(self, method: str, endpoint: str, token: str, params: Optional[Dict] = None, json_data: Optional[Dict] = None) -> (Optional[Dict], Optional[str]):
        """A centralized method for making API requests."""
        url = f"{self.BASE_URL}/{endpoint}"
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        try:
            response = self.session.request(method, url, headers=headers, params=params, json=json_data, timeout=15)
            response.raise_for_status()
            return response.json(), None
        except requests.exceptions.HTTPError as e:
            error_message = str(e)
            status_code = getattr(e.response, "status_code", "unknown")
            try:
                error_details = e.response.json().get("error", {}) if e.response is not None else {}
                error_message = error_details.get("message", str(e))
            except ValueError:
                if e.response is not None and e.response.text:
                    error_message = e.response.text.strip()[:500]
            logger.error(f"Meta API HTTP Error on {endpoint}: {error_message} (Status: {status_code})")
            return None, error_message
        except requests.exceptions.RequestException as e:
            logger.error(f"Meta API Request Failed on {endpoint}: {e}")
            return None, f"Network error: {e}"

    def get_phone_info(self, phone_number_id: str, access_token: str) -> (Optional[PhoneInfoDTO], Optional[str]):
        """Fetches the status and quality rating of a specific phone number."""
        params = {"fields": "display_phone_number,verified_name,quality_rating,status"}
        data, error = self._make_request("GET", phone_number_id, access_token, params=params)
        if error:
            return None, error
        
        # Meta returns 'name' for status, which is confusing. We map it to api_status.
        api_status = data.get("status", "UNKNOWN")

        return PhoneInfoDTO(
            display_phone_number=data.get("display_phone_number", ""),
            verified_name=data.get("verified_name", ""),
            quality_rating=data.get("quality_rating", "UNKNOWN"),
            api_status=api_status,
            id=data.get("id", "")
        ), None

    def send_text_message(self, phone_number_id: str, access_token: str, to_phone: str, body: str) -> MessageResultDTO:
        """Sends a plain text message."""
        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": to_phone,
            "type": "text",
            "text": {"body": body}
        }
        data, error = self._make_request("POST", f"{phone_number_id}/messages", access_token, json_data=payload)
        if error:
            return MessageResultDTO(success=False, error=error)
        
        message_id = data.get("messages", [{}])[0].get("id", "")
        return MessageResultDTO(success=True, message_id=message_id)

    def send_template_message(self, phone_number_id: str, access_token: str, to_phone: str, template_name: str, language: str = "en_US", components: Optional[List] = None) -> MessageResultDTO:
        """Sends a message based on a pre-approved template."""
        payload = {
            "messaging_product": "whatsapp",
            "to": to_phone,
            "type": "template",
            "template": {
                "name": template_name,
                "language": {"code": language},
                "components": components or []
            }
        }
        data, error = self._make_request("POST", f"{phone_number_id}/messages", access_token, json_data=payload)
        if error:
            return MessageResultDTO(success=False, error=error)

        message_id = data.get("messages", [{}])[0].get("id", "")
        return MessageResultDTO(success=True, message_id=message_id)


    def upload_media(self, phone_number_id: str, access_token: str, file_path: str, mime_type: str) -> MessageResultDTO:
        url = f"{self.BASE_URL}/{phone_number_id}/media"
        headers = {"Authorization": f"Bearer {access_token}"}
        try:
            with open(file_path, "rb") as f:
                files = {"file": (os.path.basename(file_path), f, mime_type)}
                data = {"messaging_product": "whatsapp"}
                response = self.session.post(url, headers=headers, files=files, data=data, timeout=60)
                response.raise_for_status()
                return MessageResultDTO(success=True, message_id=response.json().get("id"))
        except Exception as e:
            return MessageResultDTO(success=False, error=str(e))

    def send_media_message(self, phone_number_id: str, access_token: str, to_phone: str, media_id: str, media_type: str, caption: Optional[str] = None) -> MessageResultDTO:
        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": to_phone,
            "type": media_type,
            media_type: {"id": media_id}
        }
        if caption and media_type in ["image", "video", "document"]:
            payload[media_type]["caption"] = caption
        data, error = self._make_request("POST", f"{phone_number_id}/messages", access_token, json_data=payload)
        if error:
            return MessageResultDTO(success=False, error=error)
        return MessageResultDTO(success=True, message_id=data.get("messages", [{}])[0].get("id", ""))

    def get_message_templates(self, waba_id: str, access_token: str) -> (Optional[List[TemplateDTO]], Optional[str]):
        """Retrieves all message templates associated with a WABA."""
        params = {"fields": "name,status,category,language,components"}
        data, error = self._make_request("GET", f"{waba_id}/message_templates", access_token, params=params)
        if error:
            return None, error
        
        templates = []
        for item in data.get("data", []):
            components = []
            for comp_data in item.get("components", []):
                components.append(TemplateComponentDTO(
                    type=comp_data.get("type"),
                    text=comp_data.get("text"),
                    format=comp_data.get("format")
                ))
            
            templates.append(TemplateDTO(
                id=item.get("id"),
                name=item.get("name"),
                status=item.get("status"),
                category=item.get("category"),
                language=item.get("language"),
                components=components
            ))
        return templates, None

    def download_media(self, media_id: str, access_token: str) -> (bool, str):
        # First get media URL
        url = f"{self.BASE_URL}/{media_id}"
        headers = {"Authorization": f"Bearer {access_token}"}
        try:
            response = self.session.get(url, headers=headers, timeout=30)
            response.raise_for_status()
            media_url = response.json().get("url")
            if not media_url:
                return False, "Media URL not found in response"
            
            # Download the actual file
            media_response = self.session.get(media_url, headers=headers, stream=True, timeout=60)
            media_response.raise_for_status()
            
            attachments_dir = os.path.join(os.getcwd(), "attachments")
            os.makedirs(attachments_dir, exist_ok=True)
            
            # Extract extension from mime-type or Content-Type
            content_type = media_response.headers.get("Content-Type", "")
            ext = content_type.split("/")[-1] if "/" in content_type else "bin"
            if ext == "jpeg": ext = "jpg"
            
            file_path = os.path.join(attachments_dir, f"{media_id}.{ext}")
            with open(file_path, "wb") as f:
                for chunk in media_response.iter_content(chunk_size=8192):
                    f.write(chunk)
            return True, file_path
        except Exception as e:
            return False, str(e)

    def send_interactive_message(self, phone_number_id: str, access_token: str, to_phone: str, interactive_data: dict) -> MessageResultDTO:
        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": to_phone,
            "type": "interactive",
            "interactive": interactive_data
        }
        data, error = self._make_request("POST", f"{phone_number_id}/messages", access_token, json_data=payload)
        if error:
            return MessageResultDTO(success=False, error=error)
        return MessageResultDTO(success=True, message_id=data.get("messages", [{}])[0].get("id", ""))
