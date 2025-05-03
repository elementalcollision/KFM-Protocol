from locust import HttpUser, task, between
import random

# Base URL of the API Gateway
# Replace with your actual gateway URL when running
API_GATEWAY_HOST = "http://localhost:8000"

# Placeholder for API Key - Should be loaded securely in a real test environment
API_KEY = "supersecretkey" # TODO: Replace with secure loading

class KfmApiUser(HttpUser):
    """Simulates a user interacting with the KFM API Gateway."""
    host = API_GATEWAY_HOST
    wait_time = between(1, 5) # Wait 1-5 seconds between tasks

    def on_start(self):
        """Called when a Locust user starts"""
        self.headers = {
            "X-API-Key": API_KEY,
            "Content-Type": "application/json"
        }
        self.agent_ids = [] # Keep track of created agents if needed for other tasks

    @task(10) # Higher weight for discovery task
    def discover_agents(self):
        """Task simulating agent discovery calls."""
        # Example query parameters (randomize or use specific scenarios)
        params = {
            "state": random.choice(["STABLE", "EXPERIMENTAL", None]),
            "type": random.choice(["SimpleTest", "AIModelAgent", None]),
            # "limit": random.randint(10, 50) # Uncomment if API supports limit
        }
        # Remove None params
        query_params = {k: v for k, v in params.items() if v is not None}
        
        self.client.get(
            "/api/v1/agent-discovery/agents", # Assuming discovery is at /agent-discovery
            params=query_params,
            headers=self.headers,
            name="/discovery/agents" # Group stats under this name
        )

    # @task(1) # Lower weight for agent creation task
    # def create_agent(self):
    #     """Task simulating agent registration.""" 
    #     agent_data = {
    #         "name": f"LoadTestAgent-{random.randint(1000, 9999)}",
    #         "type": "LoadTest",
    #         "version": "1.0",
    #         "metadata": { "source": "locust" }
    #     }
    #     with self.client.post(
    #         "/api/v1/agent-registry/agents", 
    #         json=agent_data, # Send data as JSON
    #         headers=self.headers,
    #         catch_response=True, # Allow us to check the response
    #         name="/agents/register"
    #     ) as response:
    #         if response.status_code == 201:
    #             try:
    #                 agent_id = response.json().get("id")
    #                 if agent_id:
    #                     self.agent_ids.append(agent_id)
    #                 response.success()
    #             except Exception:
    #                 response.failure("Failed to parse agent ID from response")
    #         else:
    #             response.failure(f"Failed to register agent, status: {response.status_code}")

    # TODO: Add tasks for other scenarios:
    # - State transitions (promote, deprecate, archive, delete)
    # - F-Operator adaptation calls
    # - Policy interactions

# If running locust directly:
# locust -f tests/load/locustfile.py 