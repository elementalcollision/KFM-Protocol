from pydantic import BaseModel, Field, field_validator
from typing import Optional, Dict
import enum
import re

# Kubernetes resource quantity pattern (simplified)
# Allows integers, fractions (e.g., 100m), and units (e.g., Mi, Gi, Ti)
K8S_QUANTITY_PATTERN = r"^([0-9]+(?:\.[0-9]+)?)([EPTGMkm]|[eEinp])?i?$"

class AgentState(str, enum.Enum):
    """Agent lifecycle states."""
    NEW = "NEW"
    EXPERIMENTAL = "EXPERIMENTAL"
    CANDIDATE = "CANDIDATE"
    STABLE = "STABLE"
    DEPRECATED = "DEPRECATED"
    ARCHIVED = "ARCHIVED"
    KILLED = "KILLED"

class ResourceSpec(BaseModel):
    """Defines resource requests or limits."""
    cpu: Optional[str] = None
    memory: Optional[str] = None
    ephemeral_storage: Optional[str] = Field(None, alias="ephemeral-storage")
    nvidia_com_gpu: Optional[str] = Field(None, alias="nvidia.com/gpu") # Example for GPU

    @field_validator('cpu', 'memory', 'ephemeral_storage', 'nvidia_com_gpu')
    @classmethod
    def check_k8s_quantity_format(cls, v: Optional[str]):
        if v is None:
            return v
        if not re.match(K8S_QUANTITY_PATTERN, v):
            raise ValueError(f"Invalid Kubernetes resource quantity format: {v}")
        return v

    class Config:
        populate_by_name = True # Allow using alias for field population

class QuotaSpec(BaseModel):
    """Contains requests and limits specifications."""
    requests: Optional[ResourceSpec] = None
    limits: Optional[ResourceSpec] = None

class AgentQuotaConfig(BaseModel):
    """Root model for agent resource quota configuration."""
    defaults: QuotaSpec
    states: Dict[AgentState, QuotaSpec]

class FullQuotaConfig(BaseModel):
    """Represents the top-level structure in the YAML file."""
    agentResourceQuotas: AgentQuotaConfig 