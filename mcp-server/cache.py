"""
Caching utilities for MCP Server.
Simple in-memory cache implementation.
"""

from typing import Any, Optional
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


class CacheEntry:
    """Cache entry with TTL."""
    
    def __init__(self, value: Any, ttl: int):
        self.value = value
        self.expires_at = datetime.now() + timedelta(seconds=ttl)
    
    def is_expired(self) -> bool:
        """Check if cache entry is expired."""
        return datetime.now() >= self.expires_at


class CacheManager:
    """Simple in-memory cache manager."""
    
    def __init__(self):
        self._cache: dict[str, CacheEntry] = {}
    
    async def get(self, key: str) -> Optional[Any]:
        """
        Get value from cache.
        
        Args:
            key: Cache key
            
        Returns:
            Cached value or None if not found/expired
        """
        entry = self._cache.get(key)
        if entry is None:
            return None
        
        if entry.is_expired():
            del self._cache[key]
            return None
        
        return entry.value
    
    async def set(self, key: str, value: Any, ttl: int) -> None:
        """
        Set value in cache with TTL.
        
        Args:
            key: Cache key
            value: Value to cache
            ttl: Time to live in seconds
        """
        self._cache[key] = CacheEntry(value, ttl)
    
    async def delete(self, key: str) -> None:
        """
        Delete value from cache.
        
        Args:
            key: Cache key
        """
        self._cache.pop(key, None)
    
    async def clear(self) -> None:
        """Clear all cache entries."""
        self._cache.clear()


# Global cache manager instance
cache_manager = CacheManager()

