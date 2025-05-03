import httpx
from typing import Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)

class PolicyEngineClient:
    def __init__(self, base_url: str, auth_token: Optional[str] = None):
        self.base_url = base_url.rstrip("/")
        self.headers = {"Authorization": f"Bearer {auth_token}"} if auth_token else {}
        self.client = httpx.AsyncClient(base_url=self.base_url, headers=self.headers)

    async def validate_operation(self, validation_request: Dict[str, Any]) -> Dict[str, Any]:
        try:
            response = await self.client.post("/validate", json=validation_request)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            logger.error(f"Policy validation failed: {e}")
            return {"allowed": False, "error": str(e)}

    async def close(self):
        await self.client.aclose() 