from enum import Enum
from typing import Dict, Any, Optional

class TimeoutCategory(Enum):
    """
    Timeout categories for different types of operations.
    
    - FAST: Quick operations like health checks, simple reads (< 1s)
    - STANDARD: Normal API operations (1-5s)
    - EXTENDED: Complex operations that may take longer (5-30s)
    - LONG_RUNNING: Operations that are expected to take significant time (30s+)
    """
    FAST = 1
    STANDARD = 5
    EXTENDED = 30
    LONG_RUNNING = 120  # 2 minutes


# Mapping of services and their endpoints to timeout categories
SERVICE_TIMEOUT_MAPPINGS: Dict[str, Dict[str, TimeoutCategory]] = {
    "agent-registry": {
        "get_agent": TimeoutCategory.FAST,
        "list_agents": TimeoutCategory.FAST,
        "create_agent": TimeoutCategory.STANDARD,
        "update_agent": TimeoutCategory.STANDARD,
        "delete_agent": TimeoutCategory.STANDARD,
    },
    "f-operator": {
        "execute_function": TimeoutCategory.EXTENDED,
        "get_function_status": TimeoutCategory.FAST,
        "list_functions": TimeoutCategory.STANDARD,
    },
    "m-operator": {
        "create_model_instance": TimeoutCategory.EXTENDED,
        "get_model_instance": TimeoutCategory.FAST,
        "list_model_instances": TimeoutCategory.STANDARD,
    },
    "k-operator": {
        "get_knowledge": TimeoutCategory.STANDARD,
        "create_knowledge": TimeoutCategory.EXTENDED,
        "search_knowledge": TimeoutCategory.EXTENDED,
    }
}


def get_timeout_for_request(service: str, endpoint: str) -> int:
    """
    Get the appropriate timeout in seconds for a given service and endpoint.
    
    Args:
        service: Service name (e.g., 'agent-registry')
        endpoint: Endpoint or operation name (e.g., 'get_agent')
        
    Returns:
        int: Timeout in seconds
    """
    # Get service mappings or use standard timeout if not found
    service_mappings = SERVICE_TIMEOUT_MAPPINGS.get(service, {})
    
    # Get endpoint timeout category or use STANDARD if not found
    timeout_category = service_mappings.get(endpoint, TimeoutCategory.STANDARD)
    
    # Return the timeout in seconds
    return timeout_category.value 