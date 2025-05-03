import httpx
from typing import Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)

class AgentRegistryClient:
    def __init__(self, base_url: str, auth_token: Optional[str] = None):
        self.base_url = base_url.rstrip("/")
        self.headers = {"Authorization": f"Bearer {auth_token}"} if auth_token else {}
        self.client = httpx.AsyncClient(base_url=self.base_url, headers=self.headers)

    async def get_agent(self, agent_id: str) -> Optional[Dict[str, Any]]:
        try:
            response = await self.client.get(f"/agents/{agent_id}")
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            logger.error(f"Failed to fetch agent {agent_id}: {e}")
            return None

    async def update_agent_composition(self, agent_id: str, composition_metadata: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        try:
            response = await self.client.patch(f"/agents/{agent_id}/composition", json=composition_metadata)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            logger.error(f"Failed to update composition for agent {agent_id}: {e}")
            return None

    async def close(self):
        await self.client.aclose() 