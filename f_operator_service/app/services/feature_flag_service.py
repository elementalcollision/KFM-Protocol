import logging
from typing import List, Optional, Dict, Any
from functools import lru_cache
import hashlib

from f_operator_service.schemas.feature_flag import FeatureFlag, TargetingRule
from f_operator_service.core.config import get_settings

logger = logging.getLogger(__name__)

class FeatureFlagService:
    def __init__(self):
        self._refresh_flags()

    def _refresh_flags(self):
        """Reloads flags from the central configuration."""
        settings = get_settings() # Gets cached settings
        self._flags_map: Dict[str, FeatureFlag] = {flag.name: flag for flag in settings.feature_flags}
        logger.info(f"Feature flags refreshed. Loaded {len(self._flags_map)} flags.")

    def get_flag(self, name: str) -> Optional[FeatureFlag]:
        """Get a specific feature flag by name."""
        return self._flags_map.get(name)
    
    def get_all_flags(self) -> List[FeatureFlag]:
         """Get all loaded feature flags."""
         return list(self._flags_map.values())

    def is_flag_active(self, name: str, context: Optional[Dict[str, Any]] = None) -> bool:
        """Check if a feature flag is active, potentially based on context."""
        flag = self.get_flag(name)
        if not flag or not flag.is_active:
            return False
        if not flag.rules:
            return True
        context = context or {}
        # Evaluate rules: if any rule matches, flag is active for this context
        for rule in flag.rules:
            if self._evaluate_rule(rule, context):
                return True
        return False

    def _evaluate_rule(self, rule: TargetingRule, context: Dict[str, Any]) -> bool:
        rule_type = rule.type
        value = rule.value
        if rule_type == "percentage":
            agent_id = context.get("agent_id")
            if agent_id is None:
                logger.warning("Percentage rule requires 'agent_id' in context.")
                return False
            # Use a hash of agent_id to get a deterministic percentage
            h = int(hashlib.sha256(str(agent_id).encode()).hexdigest(), 16)
            pct = h % 100
            try:
                threshold = int(value)
            except Exception:
                logger.warning(f"Invalid percentage value for rule: {value}")
                return False
            return pct < threshold
        elif rule_type == "agent_ids":
            agent_id = context.get("agent_id")
            if agent_id is None:
                logger.warning("agent_ids rule requires 'agent_id' in context.")
                return False
            return agent_id in value
        elif rule_type == "environment":
            env = context.get("environment")
            if env is None:
                logger.warning("environment rule requires 'environment' in context.")
                return False
            if isinstance(value, list):
                return env in value
            return env == value
        else:
            logger.warning(f"Unknown rule type: {rule_type}")
            return False

# Singleton instance (consider dependency injection later)
# Use lru_cache to make it a singleton-like function
@lru_cache(maxsize=None)
def get_feature_flag_service() -> FeatureFlagService:
    return FeatureFlagService() 