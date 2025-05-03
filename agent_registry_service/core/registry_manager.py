import asyncio
import logging
from typing import Dict, List, Optional, Tuple, Any
from uuid import UUID
import json
import hashlib
from datetime import datetime

import redis.asyncio as redis
from sqlalchemy.ext.asyncio import AsyncSession
from prometheus_client import Counter # For metrics

from agent_registry_service.models import AgentRegistryEntryModel, Subscription # Import Subscription for type hints if needed
from agent_registry_service.schemas import (
    AgentRegistryEntry, AgentCreateSchema, AgentUpdateSchema,
    DiscoveryCriteria, DiscoverySortOptions, CapabilityMatchType, AgentState
)
from agent_registry_service import crud
from agent_registry_service.db.cache import get_redis_client # Import redis dependency
# from agent_registry_service.core.config import get_settings # Import settings if needed for TTL

logger = logging.getLogger(__name__)

# --- Prometheus Metrics ---
# Assumes a registry is configured and passed or available globally
# Example: from app.monitoring import REGISTRY
DISCOVERY_CACHE_HITS = Counter(
    'discovery_cache_hits_total', 
    'Total cache hits for agent discovery queries',
    # registry=REGISTRY 
)
DISCOVERY_CACHE_MISSES = Counter(
    'discovery_cache_misses_total', 
    'Total cache misses for agent discovery queries',
    # registry=REGISTRY
)
# ------------------------


class RegistryManager:
    _instance = None

    def __new__(cls, *args, **kwargs): # Accept args/kwargs for init
        if cls._instance is None:
            cls._instance = super(RegistryManager, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self, redis_client: redis.Redis, cache_ttl: int):
        # Pass redis_client and cache_ttl during instantiation
        if self._initialized:
            return
        
        self._registry: Dict[UUID, AgentRegistryEntry] = {}
        self._lock = asyncio.Lock()
        self.redis_client = redis_client
        self.cache_ttl = cache_ttl
        self.cache_prefix = "discovery_cache"
        self.event_channel = "agent_registry_events" # Define channel name
        self._initialized = True
        logger.info(f"Registry Manager initialized (singleton) with cache TTL: {cache_ttl}s")

    # --- Event Publishing --- 
    async def _publish_agent_event(self, event_type: str, agent_data: Dict):
        """Publishes an agent change event to Redis Pub/Sub."""
        if not self.redis_client:
             logger.warning("Redis client not available, skipping event publish.")
             return
        try:
            message = json.dumps({
                "event_type": event_type,
                "timestamp": datetime.utcnow().isoformat(),
                "agent_id": str(agent_data.get('id')), # Ensure ID is string for JSON
                "agent_data": agent_data # Include full data for create/update
            })
            await self.redis_client.publish(self.event_channel, message)
            logger.info(f"Published '{event_type}' event to {self.event_channel} for agent {agent_data.get('id')}")
        except redis.RedisError as e:
            logger.error(f"Redis PUBLISH error to channel {self.event_channel}: {e}", exc_info=True)
        except Exception as e:
            logger.error(f"Unexpected error publishing agent event: {e}", exc_info=True)

    async def _publish_agent_delete_event(self, agent_id: UUID):
        """Publishes an agent delete event."""
        if not self.redis_client:
             logger.warning("Redis client not available, skipping event publish.")
             return
        try:
            message = json.dumps({
                "event_type": "agent_deleted",
                "timestamp": datetime.utcnow().isoformat(),
                "agent_id": str(agent_id),
                "agent_data": None # No data for delete event
            })
            await self.redis_client.publish(self.event_channel, message)
            logger.info(f"Published 'agent_deleted' event to {self.event_channel} for agent {agent_id}")
        except redis.RedisError as e:
            logger.error(f"Redis PUBLISH error for delete event: {e}", exc_info=True)
        except Exception as e:
            logger.error(f"Unexpected error publishing agent delete event: {e}", exc_info=True)

    # --- Cache Key Generation --- 
    def _generate_discovery_cache_key(self, criteria: DiscoveryCriteria) -> str:
         """Generates a stable cache key from discovery criteria."""
         # Create a dict of relevant criteria for hashing
         # Exclude pagination for broader cache hits? Or include for exact match?
         # Including pagination for now for simplicity.
         # Exclude defaults to simplify key if possible, but might cause subtle issues.
         key_data = criteria.model_dump(exclude_defaults=False) 
         
         # Sort dict for consistent hash
         serialized_data = json.dumps(key_data, sort_keys=True)
         
         hasher = hashlib.md5()
         hasher.update(serialized_data.encode('utf-8'))
         key_hash = hasher.hexdigest()
         
         cache_key = f"{self.cache_prefix}:{key_hash}"
         logger.debug(f"Generated cache key '{cache_key}' for criteria: {key_data}")
         return cache_key

    # --- Cache Invalidation --- 
    async def _invalidate_discovery_cache(self):
        """Invalidates all discovery cache entries (Broad Invalidation)."""
        pattern = f"{self.cache_prefix}:*"
        logger.info(f"Invalidating discovery cache with pattern: {pattern}")
        try:
            keys = await self.redis_client.keys(pattern)
            if keys:
                deleted_count = await self.redis_client.delete(*keys)
                logger.info(f"Invalidated {deleted_count} discovery cache keys.")
            else:
                logger.info("No discovery cache keys found to invalidate.")
        except redis.RedisError as e:
            logger.error(f"Error invalidating discovery cache: {e}", exc_info=True)
        except Exception as e:
             logger.error(f"Unexpected error during cache invalidation: {e}", exc_info=True)

    # --- Core Methods (Modified for Cache & Invalidation) ---

    async def initialize_from_db(self, db: AsyncSession):
        """Load all agent entries from database into memory on startup."""
        async with self._lock:
            if not self._registry: # Only load if registry is empty
                logger.info("Loading agent registry from database...")
                try:
                    db_entries: List[AgentRegistryEntryModel] = await crud.get_all_agent_entries(db, limit=10000) # Load all initially
                    # Convert DB models to Pydantic schemas for in-memory store
                    self._registry = {entry.id: AgentRegistryEntry.from_orm(entry) for entry in db_entries}
                    logger.info(f"Loaded {len(self._registry)} agent entries into registry.")
                except Exception as e:
                    logger.error(f"Failed to load agent registry from DB: {e}", exc_info=True)
            else:
                 logger.info("Registry already populated, skipping DB load.")

    async def register_agent(self, *, obj_in: AgentCreateSchema, db: AsyncSession) -> AgentRegistryEntry:
        """Register a new agent in both database and memory, then invalidate cache and publish event."""
        db_obj = await crud.create_agent_entry(db, obj_in=obj_in)
        agent_entry = AgentRegistryEntry.from_orm(db_obj)
        
        async with self._lock:
            self._registry[agent_entry.id] = agent_entry
            logger.info(f"Registered agent {agent_entry.id} in memory.")
            
        # Invalidate cache & publish event after successful registration
        await self._invalidate_discovery_cache()
        await self._publish_agent_event("agent_created", agent_entry.model_dump())
        return agent_entry

    async def get_agent(self, agent_id: UUID) -> Optional[AgentRegistryEntry]:
        """Get agent from in-memory store."""
        return self._registry.get(agent_id)

    async def get_all_agents(self) -> List[AgentRegistryEntry]:
        """Get all agents from in-memory store."""
        return list(self._registry.values())

    async def discover_agents(self, criteria: DiscoveryCriteria) -> Tuple[List[AgentRegistryEntry], int]:
        """Discover agents based on complex criteria, checking cache first."""
        logger.debug(f"Discovering agents with criteria: {criteria.model_dump()}")
        cache_key = self._generate_discovery_cache_key(criteria)
        
        # 1. Check Cache
        try:
            cached_data = await self.redis_client.get(cache_key)
            if cached_data:
                logger.info(f"Cache hit for key: {cache_key}")
                DISCOVERY_CACHE_HITS.inc()
                # Deserialize cached data (expected format: [agent_list_json, total_count])
                cached_result = json.loads(cached_data)
                # Re-parse agent list into Pydantic models
                agents = [AgentRegistryEntry.model_validate(agent_dict) for agent_dict in cached_result[0]]
                total = cached_result[1]
                return agents, total
        except redis.RedisError as e:
            logger.error(f"Redis GET error for key {cache_key}: {e}", exc_info=True)
            # Proceed as cache miss if Redis fails
        except json.JSONDecodeError as e:
            logger.error(f"Error decoding cached data for key {cache_key}: {e}", exc_info=True)
            # Treat as cache miss, potentially delete invalid key?
            # await self.redis_client.delete(cache_key)
        except Exception as e:
             logger.error(f"Unexpected error during cache check for key {cache_key}: {e}", exc_info=True)

        # 2. Cache Miss - Execute Discovery Logic
        logger.info(f"Cache miss for key: {cache_key}. Executing discovery logic.")
        DISCOVERY_CACHE_MISSES.inc()
        
        async with self._lock: # Lock for reading the registry
            candidate_agents = list(self._registry.values())

        # Filtering logic (as implemented before) ...
        # 1. Filter by State
        allowed_states = set(criteria.include_states) if criteria.include_states else {AgentState.STABLE, AgentState.EXPERIMENTAL}
        filtered_agents = [agent for agent in candidate_agents if agent.state in allowed_states]
        logger.debug(f"After state filter ({allowed_states}): {len(filtered_agents)} agents")
        
        if criteria.state and not criteria.include_states:
             filtered_agents = [agent for agent in filtered_agents if agent.state == criteria.state]
             logger.debug(f"After specific state filter ({criteria.state}): {len(filtered_agents)} agents")
        elif criteria.state and criteria.include_states:
             logger.warning("Both 'state' and 'include_states' provided in discovery criteria. 'include_states' takes precedence.")

        # 2. Filter by Type
        if criteria.type:
            filtered_agents = [agent for agent in filtered_agents if agent.type == criteria.type]
            logger.debug(f"After type filter ('{criteria.type}'): {len(filtered_agents)} agents")

        # 3. Filter by Metadata
        if criteria.metadata_filters:
            agents_matching_meta = []
            for agent in filtered_agents:
                match = True
                agent_meta = agent.metadata_ if isinstance(agent.metadata_, dict) else {}
                for key, value in criteria.metadata_filters.items():
                    if agent_meta.get(key) != value:
                        match = False
                        break
                if match:
                    agents_matching_meta.append(agent)
            filtered_agents = agents_matching_meta
            logger.debug(f"After metadata filter ({criteria.metadata_filters}): {len(filtered_agents)} agents")

        # 4. Filter by Capabilities
        if criteria.capabilities:
            required_caps = set(c.lower() for c in criteria.capabilities) # Normalize case
            agents_matching_caps = []
            for agent in filtered_agents:
                agent_caps = set(c.lower() for c in agent.capabilities) # Normalize case
                match = False
                if criteria.capability_match_type == CapabilityMatchType.EXACT:
                    match = required_caps.issubset(agent_caps)
                elif criteria.capability_match_type == CapabilityMatchType.ANY:
                    match = not required_caps.isdisjoint(agent_caps)
                # TODO: Add FUZZY match logic here if needed
                if match:
                    agents_matching_caps.append(agent)
            filtered_agents = agents_matching_caps
            logger.debug(f"After capability filter ({criteria.capabilities}, mode={criteria.capability_match_type.value}): {len(filtered_agents)} agents")

        total_count = len(filtered_agents)
        logger.debug(f"Total matching agents before sorting/pagination: {total_count}")

        # 5. Sorting ... (logic remains the same as previous edit)
        sort_field = "created_at"
        sort_desc = True
        if criteria.sort_by:
            sort_parts = criteria.sort_by.value.split('_')
            sort_field = "_".join(sort_parts[:-1])
            sort_desc = sort_parts[-1] == "desc"
            if sort_field not in AgentRegistryEntry.model_fields:
                 logger.warning(f"Invalid sort field '{sort_field}'. Defaulting to created_at.")
                 sort_field = "created_at"
                 sort_desc = True
        logger.debug(f"Sorting by '{sort_field}' (desc={sort_desc})")
        try:
            # Ensure getattr default is appropriate for comparison or handle None
            filtered_agents.sort(key=lambda agent: getattr(agent, sort_field, agent.created_at), reverse=sort_desc)
        except TypeError:
            logger.warning(f"Cannot sort by field '{sort_field}'. Using default sort.")
            filtered_agents.sort(key=lambda agent: agent.created_at, reverse=True)
            
        # 6. Pagination
        skip = criteria.pagination.skip
        limit = criteria.pagination.limit
        paginated_agents = filtered_agents[skip : skip + limit]
        logger.debug(f"Applied pagination: skip={skip}, limit={limit}. Returning {len(paginated_agents)} agents.")

        # 7. Store result in Cache
        try:
            # Serialize agent list for caching (only store data, not objects)
            agents_to_cache = [agent.model_dump() for agent in paginated_agents]
            result_to_cache = [agents_to_cache, total_count]
            await self.redis_client.setex(cache_key, self.cache_ttl, json.dumps(result_to_cache))
            logger.info(f"Stored result in cache for key: {cache_key} with TTL: {self.cache_ttl}s")
        except redis.RedisError as e:
            logger.error(f"Redis SETEX error for key {cache_key}: {e}", exc_info=True)
        except Exception as e:
             logger.error(f"Unexpected error during cache storage for key {cache_key}: {e}", exc_info=True)

        return paginated_agents, total_count

    async def update_agent(self, *, agent_id: UUID, obj_in: AgentUpdateSchema, db: AsyncSession) -> Optional[AgentRegistryEntry]:
        """Update agent in both database and memory, then invalidate cache and publish event."""
        db_obj = await crud.get_agent_entry(db, agent_id=agent_id)
        if not db_obj:
            return None
        updated_db_obj = await crud.update_agent_entry(db, db_obj=db_obj, obj_in=obj_in)
        updated_agent_entry = AgentRegistryEntry.from_orm(updated_db_obj)
        async with self._lock:
            if agent_id in self._registry:
                self._registry[agent_id] = updated_agent_entry
                logger.info(f"Updated agent {agent_id} in memory.")
            else:
                 logger.warning(f"Agent {agent_id} found in DB but not in memory during update. Adding.")
                 self._registry[agent_id] = updated_agent_entry
        # Invalidate cache & publish event
        await self._invalidate_discovery_cache()
        await self._publish_agent_event("agent_updated", updated_agent_entry.model_dump())
        return updated_agent_entry

    async def deregister_agent(self, *, agent_id: UUID, db: AsyncSession) -> bool:
        """Remove agent from both database and memory, then invalidate cache and publish event."""
        deleted_obj = await crud.delete_agent_entry(db, agent_id=agent_id)
        success = False
        if deleted_obj:
            async with self._lock:
                if agent_id in self._registry:
                    del self._registry[agent_id]
                    logger.info(f"Deregistered agent {agent_id} from memory.")
                    success = True
                else:
                    logger.warning(f"Agent {agent_id} deleted from DB but was not found in memory.")
                    success = True # Still successful as it's gone from DB
            # Invalidate cache & publish delete event
            await self._invalidate_discovery_cache()
            await self._publish_agent_delete_event(agent_id)
            return success
        else:
             async with self._lock:
                 if agent_id in self._registry:
                     logger.warning(f"Agent {agent_id} not found in DB but existed in memory. Removing from memory.")
                     del self._registry[agent_id]
                     # Invalidate cache even if only memory was inconsistent
                     await self._invalidate_discovery_cache()
                     # Publish delete event even if only found in memory (to ensure consistency)
                     await self._publish_agent_delete_event(agent_id)
             return False # Indicate agent was not found in DB

# --- Singleton Instance and Dependency --- 

# Global instance of the manager - Needs modification for dependency injection
# registry_manager = RegistryManager() # Remove direct instantiation

# FastAPI dependency provider - Needs modification for dependency injection
# async def get_registry_manager() -> RegistryManager:
#     # Instance is already created, just return it
#     return registry_manager

# --- Revised Dependency Setup (Conceptual - implement in main.py or deps.py) ---
_registry_manager_instance: Optional[RegistryManager] = None

async def get_registry_manager_dep(redis_client: redis.Redis = Depends(get_redis_client)) -> RegistryManager:
    global _registry_manager_instance
    if _registry_manager_instance is None:
        settings = get_settings() # Fetch settings
        logger.info("Creating RegistryManager singleton instance.")
        _registry_manager_instance = RegistryManager(redis_client=redis_client, cache_ttl=settings.DISCOVERY_CACHE_TTL_SECONDS)
        # Initialization from DB should happen during app startup (lifespan manager)
    return _registry_manager_instance 