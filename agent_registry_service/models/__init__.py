from .base_class import Base  # Make sure Base is available

# Import existing models if any, e.g.:
# from .agent import AgentModel 
# from .metadata import MetadataModel
# from .log import LogModel

# Import the new model
from .agent_registry_entry import AgentRegistryEntryModel, AgentState
from .subscription import Subscription # Add subscription model 