import os
import httpx
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

class ApiClient:
    """
    A unified HTTP client for communicating with the SmartSafe FastAPI backend.
    Used by the desktop app when running in HYBRID or CLOUD mode.
    """
    
    def __init__(self, base_url: str = None, api_key: str = None):
        self.base_url = base_url or os.getenv("CLOUD_API_URL", "http://localhost:8000/v1")
        self.api_key = api_key
        self.client = httpx.Client(
            base_url=self.base_url,
            timeout=30.0,
            headers=self._get_headers()
        )

    def _get_headers(self) -> Dict[str, str]:
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        if self.api_key:
            headers["X-API-Key"] = self.api_key
        return headers

    def set_api_key(self, api_key: str):
        self.api_key = api_key
        self.client.headers.update(self._get_headers())

    def get(self, endpoint: str, params: Optional[Dict[str, Any]] = None) -> Any:
        try:
            response = self.client.get(endpoint, params=params)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            logger.error(f"API GET {endpoint} failed: {e}")
            raise

    def post(self, endpoint: str, data: Dict[str, Any]) -> Any:
        try:
            response = self.client.post(endpoint, json=data)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            logger.error(f"API POST {endpoint} failed: {e}")
            raise

    def post_multipart(self, endpoint: str, data: Dict[str, Any], file_path: str) -> Any:
        try:
            with open(file_path, "rb") as f:
                files = {"file": (os.path.basename(file_path), f)}
                headers = self._get_headers()
                if "Content-Type" in headers:
                    del headers["Content-Type"]
                response = self.client.post(endpoint, data=data, files=files, headers=headers)
                response.raise_for_status()
                return response.json()
        except httpx.HTTPError as e:
            logger.error(f"API POST_MULTIPART {endpoint} failed: {e}")
            raise

    def close(self):
        self.client.close()
