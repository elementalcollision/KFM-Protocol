import yaml
import logging
from typing import Optional, Dict
from pydantic import ValidationError

from resource_manager_service.core.config import settings
from resource_manager_service.schemas.quota import ( # Import models
    FullQuotaConfig, AgentQuotaConfig, QuotaSpec, AgentState, ResourceSpec
)

logger = logging.getLogger(__name__)

class QuotaService:
    """Manages loading, validation, and access to resource quota configurations."""

    def __init__(self, config_path: str = settings.CONFIG_QUOTA_FILE):
        self.config_path = config_path
        self.quota_config: Optional[AgentQuotaConfig] = None
        self.load_quotas() # Load quotas on initialization

    def load_quotas(self) -> bool:
        """Loads and validates quotas from the configured YAML file."""
        logger.info(f"Attempting to load resource quotas from: {self.config_path}")
        try:
            with open(self.config_path, 'r') as f:
                raw_config = yaml.safe_load(f)
                
            if not raw_config:
                logger.error(f"Quota configuration file is empty: {self.config_path}")
                self.quota_config = None
                return False

            # Validate the raw data against the Pydantic model
            validated_config = FullQuotaConfig(**raw_config)
            self.quota_config = validated_config.agentResourceQuotas
            logger.info(f"Successfully loaded and validated resource quotas from {self.config_path}")
            return True
            
        except FileNotFoundError:
            logger.error(f"Quota configuration file not found: {self.config_path}")
            self.quota_config = None
            return False
        except yaml.YAMLError as e:
            logger.error(f"Error parsing YAML configuration file {self.config_path}: {e}")
            self.quota_config = None
            return False
        except ValidationError as e:
            logger.error(f"Quota configuration validation failed: {e}")
            self.quota_config = None
            return False
        except Exception as e:
            logger.error(f"An unexpected error occurred while loading quotas: {e}", exc_info=True)
            self.quota_config = None
            return False

    def get_effective_quota(self, state: AgentState) -> Optional[QuotaSpec]:
        """Gets the effective quota for a given state, merging defaults and state-specific rules."""
        if not self.quota_config:
            logger.warning("Quota configuration not loaded, cannot determine effective quota.")
            return None

        default_quota = self.quota_config.defaults
        state_quota = self.quota_config.states.get(state)

        effective_requests = default_quota.requests.model_copy(deep=True) if default_quota.requests else ResourceSpec()
        effective_limits = default_quota.limits.model_copy(deep=True) if default_quota.limits else ResourceSpec()

        if state_quota:
            if state_quota.requests:
                effective_requests = effective_requests.model_copy(update=state_quota.requests.model_dump(exclude_unset=True), deep=True)
            if state_quota.limits:
                effective_limits = effective_limits.model_copy(update=state_quota.limits.model_dump(exclude_unset=True), deep=True)

        return QuotaSpec(requests=effective_requests, limits=effective_limits)

# Example of how to potentially use it (e.g., in main.py or as a dependency)
# quota_service = QuotaService()
# if quota_service.quota_config:
#    stable_quota = quota_service.get_effective_quota(AgentState.STABLE)
#    if stable_quota:
#        print(f"Stable CPU Limit: {stable_quota.limits.cpu}") 