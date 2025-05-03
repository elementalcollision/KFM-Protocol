import httpx
from typing import Optional, Dict, Any
import logging

# Assuming agent_registry_service URL is configured via environment or a config file
# For now, let's use a placeholder. In a real setup, this would come from settings.
# from k_operator_service.core.config import settings
AGENT_REGISTRY_BASE_URL = "http://localhost:8000" # Placeholder - Replace with actual config loading

logger = logging.getLogger(__name__)

class AgentRegistryError(Exception):
    """Custom exception for Agent Registry client errors."""
    def __init__(self, status_code: int, detail: Any):
        self.status_code = status_code
        self.detail = detail
        super().__init__(f"Agent Registry API error {status_code}: {detail}")


class AgentRegistryClient:
    """Client for interacting with the Agent Registry Service API."""

    def __init__(self, base_url: str = AGENT_REGISTRY_BASE_URL, timeout: int = 10):
        # In a real app, base_url would likely come from settings
        # self.base_url = settings.AGENT_REGISTRY_SERVICE_URL
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout

    async def _request(self, method: str, endpoint: str, **kwargs) -> httpx.Response:
        """Makes an async HTTP request to the Agent Registry Service."""
        url = f"{self.base_url}{endpoint}"
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                logger.debug(f"Sending {method} request to {url} with kwargs: {kwargs}")
                response = await client.request(method, url, **kwargs)
                logger.debug(f"Received response {response.status_code} from {url}")
                response.raise_for_status() # Raise HTTPStatusError for 4xx/5xx responses
                return response
            except httpx.TimeoutException as e:
                logger.error(f"Request to {url} timed out: {e}")
                raise AgentRegistryError(status_code=408, detail="Request timed out") from e
            except httpx.RequestError as e:
                logger.error(f"An error occurred while requesting {url}: {e}")
                raise AgentRegistryError(status_code=503, detail=f"Service unavailable: {e}") from e
            except httpx.HTTPStatusError as e:
                logger.error(f"HTTP error {e.response.status_code} for {url}: {e.response.text}")
                try:
                    detail = e.response.json()
                except Exception:
                    detail = e.response.text
                raise AgentRegistryError(status_code=e.response.status_code, detail=detail) from e

    async def set_agent_state(self, agent_id: str, state: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Sets the state of a specific agent in the registry.

        Args:
            agent_id: The ID of the agent.
            state: The target state (e.g., 'DEPRECATED', 'ARCHIVED').
            context: Optional context for the state transition.

        Returns:
            The JSON response body from the Agent Registry API.

        Raises:
            AgentRegistryError: If the API call fails.
        """
        endpoint = f"/api/v1/agents/{agent_id}/state"
        payload = {"state": state}
        if context:
            payload["context"] = context

        response = await self._request("PUT", endpoint, json=payload)
        return response.json()

    async def delete_agent(self, agent_id: str) -> None:
        """Deletes a specific agent from the registry.

        Args:
            agent_id: The ID of the agent to delete.

        Raises:
            AgentRegistryError: If the API call fails.
        """
        endpoint = f"/api/v1/agents/{agent_id}"
        await self._request("DELETE", endpoint)
        # DELETE typically returns 204 No Content on success, no body to parse
        logger.info(f"Successfully initiated deletion for agent {agent_id} via Agent Registry.")

# Example Usage (within an async function):
# async def main():
#     client = AgentRegistryClient()
#     try:
#         # Deprecate an agent
#         result = await client.set_agent_state('agent-abc', 'DEPRECATED', {'reason': 'Old version'})
#         print(f"State transition result: {result}")
#
#         # Delete an agent (assuming it's in ARCHIVED state)
#         await client.delete_agent('agent-xyz')
#         print("Deletion initiated for agent-xyz")
#
#     except AgentRegistryError as e:
#         print(f"API Error ({e.status_code}): {e.detail}")
#
# if __name__ == "__main__":
#     import asyncio
#     # Configure basic logging for example run
#     logging.basicConfig(level=logging.DEBUG)
#     asyncio.run(main()) 