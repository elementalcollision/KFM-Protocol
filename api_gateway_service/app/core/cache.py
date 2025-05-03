import time
import logging
from typing import Dict, Any, Optional, Tuple, List
from datetime import datetime, timedelta
from functools import lru_cache
import asyncio

logger = logging.getLogger(__name__)


class CacheEntry:
    """
    Cache entry with expiration time.
    """
    def __init__(self, data: Any, ttl_seconds: int):
        """
        Initialize cache entry.
        
        Args:
            data: Data to cache.
            ttl_seconds: Time-to-live in seconds.
        """
        self.data = data
        self.expiry = time.time() + ttl_seconds
        self.created_at = time.time()
        
    def is_valid(self) -> bool:
        """
        Check if cache entry is still valid.
        
        Returns:
            bool: True if valid, False if expired.
        """
        return time.time() < self.expiry
        
    def time_remaining(self) -> float:
        """
        Get remaining time until expiry in seconds.
        
        Returns:
            float: Seconds until expiry, or 0 if expired.
        """
        return max(0, self.expiry - time.time())
        
    def age(self) -> float:
        """
        Get age of cache entry in seconds.
        
        Returns:
            float: Age in seconds.
        """
        return time.time() - self.created_at


class ResponseCache:
    """
    Simple in-memory cache for API responses.
    
    Features:
    - Time-based expiration
    - LRU eviction when capacity is reached
    - Async-safe operations
    """
    def __init__(self, max_size: int = 1000):
        """
        Initialize cache.
        
        Args:
            max_size: Maximum number of items to store.
        """
        self.cache: Dict[str, CacheEntry] = {}
        self.max_size = max_size
        self.access_order: List[str] = []  # For LRU tracking
        self._lock = asyncio.Lock()
        
    async def get(self, key: str) -> Optional[Any]:
        """
        Get data from cache if available and not expired.
        
        Args:
            key: Cache key.
            
        Returns:
            Optional[Any]: Cached data if available, None otherwise.
        """
        async with self._lock:
            if key in self.cache:
                entry = self.cache[key]
                
                if entry.is_valid():
                    # Update access order for LRU
                    if key in self.access_order:
                        self.access_order.remove(key)
                    self.access_order.append(key)
                    
                    logger.debug(f"Cache hit for key: {key}")
                    return entry.data
                else:
                    # Remove expired entry
                    logger.debug(f"Cache expired for key: {key}")
                    self._remove_entry(key)
                    
            logger.debug(f"Cache miss for key: {key}")
            return None
            
    async def set(self, key: str, value: Any, ttl_seconds: int = 60) -> None:
        """
        Store data in cache with expiration.
        
        Args:
            key: Cache key.
            value: Data to cache.
            ttl_seconds: Time-to-live in seconds.
        """
        async with self._lock:
            # Evict items if at capacity
            if len(self.cache) >= self.max_size and key not in self.cache:
                self._evict_lru()
                
            # Store the new entry
            self.cache[key] = CacheEntry(value, ttl_seconds)
            
            # Update access order for LRU
            if key in self.access_order:
                self.access_order.remove(key)
            self.access_order.append(key)
            
            logger.debug(f"Cached data for key: {key} with TTL: {ttl_seconds}s")
            
    async def delete(self, key: str) -> bool:
        """
        Delete an item from the cache.
        
        Args:
            key: Cache key.
            
        Returns:
            bool: True if item was deleted, False if not found.
        """
        async with self._lock:
            if key in self.cache:
                self._remove_entry(key)
                logger.debug(f"Deleted cache entry for key: {key}")
                return True
            return False
            
    async def clear(self) -> None:
        """Clear all items from cache."""
        async with self._lock:
            self.cache.clear()
            self.access_order.clear()
            logger.debug("Cache cleared")
            
    async def get_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.
        
        Returns:
            Dict[str, Any]: Statistics about the cache.
        """
        async with self._lock:
            return {
                "size": len(self.cache),
                "max_size": self.max_size,
                "usage_percent": (len(self.cache) / self.max_size) * 100 if self.max_size > 0 else 0,
                "keys": list(self.cache.keys()),
            }
    
    def _remove_entry(self, key: str) -> None:
        """
        Remove an entry from the cache.
        
        Args:
            key: Cache key.
        """
        if key in self.cache:
            del self.cache[key]
        if key in self.access_order:
            self.access_order.remove(key)
            
    def _evict_lru(self) -> None:
        """Evict the least recently used item from the cache."""
        if self.access_order:
            lru_key = self.access_order.pop(0)
            if lru_key in self.cache:
                del self.cache[lru_key]
                logger.debug(f"Evicted LRU cache entry: {lru_key}")


# Singleton instance
_cache = ResponseCache()


def get_response_cache() -> ResponseCache:
    """
    Get the singleton response cache instance.
    
    Returns:
        ResponseCache: The response cache.
    """
    return _cache 