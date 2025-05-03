import logging
from typing import Dict, Any, Optional
import hashlib

# Assume config service integration or direct loading for base flags
# from f_operator_service.core.config import get_settings 

logger = logging.getLogger(__name__)

class FeatureFlagService:
    def __init__(self, config_source: Optional[Dict] = None):
        # Load base flags from config source (e.g., settings object or config file)
        # self.settings = get_settings()
        # self.base_flags = self.settings.FEATURE_FLAGS or {}
        self.base_flags = config_source.get("FEATURE_FLAGS", {}) if config_source else {}
        logger.info(f"Initialized FeatureFlagService with {len(self.base_flags)} base flags.")
        
        # In-memory store for dynamic overrides (e.g., from experiments)
        self.dynamic_flags: Dict[str, Dict] = {}

    def set_dynamic_flag_override(self, flag_name: str, override_config: Dict):
        """Set or update a dynamic override for a feature flag (e.g., for an experiment)."""
        logger.info(f"Setting dynamic override for flag '{flag_name}': {override_config}")
        self.dynamic_flags[flag_name] = override_config

    def remove_dynamic_flag_override(self, flag_name: str):
        """Remove a dynamic override for a feature flag."""
        if flag_name in self.dynamic_flags:
            logger.info(f"Removing dynamic override for flag '{flag_name}'")
            del self.dynamic_flags[flag_name]
        else:
            logger.debug(f"Attempted to remove non-existent dynamic override for flag '{flag_name}'")

    async def is_flag_active(self, flag_name: str, context: Optional[Dict[str, Any]] = None) -> bool:
        """Check if a feature flag is active, considering dynamic overrides and targeting rules."""
        context = context or {}
        logger.debug(f"Evaluating flag '{flag_name}' with context: {context}")

        # Check dynamic overrides first (e.g., from active experiments)
        if flag_name in self.dynamic_flags:
            logger.debug(f"Found dynamic override for flag '{flag_name}'")
            return self._evaluate_flag_config(self.dynamic_flags[flag_name], context)
            
        # Fall back to base configuration flags
        if flag_name in self.base_flags:
            logger.debug(f"Evaluating base config for flag '{flag_name}'")
            return self._evaluate_flag_config(self.base_flags[flag_name], context)
            
        # Default to False if flag is unknown
        logger.warning(f"Flag '{flag_name}' not found in base or dynamic config. Defaulting to False.")
        return False
        
    def _evaluate_flag_config(self, flag_config: Any, context: Dict[str, Any]) -> bool:
        """Evaluate a specific flag configuration (could be bool or dict with rules)."""
        # Simple boolean flag
        if isinstance(flag_config, bool):
            logger.debug(f"Flag config is simple boolean: {flag_config}")
            return flag_config
            
        # Advanced configuration with rules
        if isinstance(flag_config, dict):
            # Check global active status first
            if not flag_config.get("is_active", False):
                logger.debug("Flag is globally inactive.")
                return False
                
            # Check targeting rules if present
            targeting_rules = flag_config.get("targeting")
            if targeting_rules:
                 if not self._evaluate_targeting(targeting_rules, context):
                     logger.debug("Context did not match targeting rules.")
                     return False # Did not match targeting rules
                 else:
                      logger.debug("Context matched targeting rules.")
                      # Matched rules, flag is active for this context
                      return True 
            else:
                # No targeting rules, flag is active if is_active=True
                logger.debug("Flag is active (no targeting rules).")
                return True 
        
        # Invalid config type
        logger.error(f"Invalid flag configuration type: {type(flag_config)}")
        return False
            
    def _evaluate_targeting(self, targeting_rules: Dict, context: Dict[str, Any]) -> bool:
        """Evaluate targeting rules against the provided context."""
        # Example: Percentage rollout based on user_id
        if "percentage" in targeting_rules:
            percentage = targeting_rules["percentage"]
            user_id = context.get("user_id")
            if user_id:
                # Use a consistent hashing algorithm (e.g., MD5) 
                # Ensure the hash target is stable (e.g., flag name + user id + seed)
                seed = targeting_rules.get('seed', 'default_seed')
                hash_input = f"{user_id}:{seed}".encode()
                hash_val = int(hashlib.md5(hash_input).hexdigest(), 16)
                user_percentage = (hash_val % 100) + 1 # Range 1-100
                
                if user_percentage <= percentage:
                    logger.debug(f"Percentage rollout matched ({user_percentage}% <= {percentage}%)")
                    return True # User falls within the percentage
                else:
                    logger.debug(f"Percentage rollout did not match ({user_percentage}% > {percentage}%)")
                    return False
            else:
                # No user_id provided, cannot evaluate percentage rollout
                logger.debug("Percentage targeting requires user_id in context.")
                return False
        
        # Example: Environment targeting
        if "environments" in targeting_rules:
            target_envs = targeting_rules["environments"]
            current_env = context.get("environment")
            if current_env and current_env in target_envs:
                 logger.debug(f"Environment targeting matched ('{current_env}' in {target_envs})")
                 return True
            else:
                 logger.debug(f"Environment targeting did not match ('{current_env}' not in {target_envs})")
                 return False
                 
        # Example: User segment targeting
        if "user_segments" in targeting_rules:
             target_segments = set(targeting_rules["user_segments"])
             user_segments = set(context.get("user_segments", []))
             if target_segments.intersection(user_segments):
                 logger.debug("User segment targeting matched.")
                 return True
             else:
                 logger.debug("User segment targeting did not match.")
                 return False

        # Add more rule types as needed (e.g., custom attributes, time-based)
        
        # Default: If no specific targeting rules matched/failed, assume match
        # This might need adjustment based on desired default behavior
        logger.debug("No specific targeting rules applied or failed, assuming match.")
        return True

# Example usage (dependency injection pattern)
# feature_flag_service = FeatureFlagService(config_source=get_settings().dict())
# def get_feature_flag_service():
#    return feature_flag_service 