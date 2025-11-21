"""
Agno Redis Storage Integration
================================
Provides Redis-based storage for Agno agent session history and context.
This enables the agent to remember previous conversations across the session.
"""

import os
import logging
from typing import Optional
from dotenv import load_dotenv
from agno.db.redis import RedisDb

load_dotenv()

logger = logging.getLogger(__name__)


class AgnoRedisStorage:
    """Wrapper for Agno Redis storage configuration."""
    
    def __init__(self):
        """Initialize Redis storage for Agno."""
        redis_host = os.getenv("REDIS_HOST", "localhost")
        redis_port = int(os.getenv("REDIS_PORT", "6379"))
        redis_password = os.getenv("REDIS_PASSWORD")
        redis_db = int(os.getenv("REDIS_DB", "0"))
        
        # Build Redis URL
        if redis_password:
            redis_url = f"redis://:{redis_password}@{redis_host}:{redis_port}/{redis_db}"
        else:
            redis_url = f"redis://{redis_host}:{redis_port}/{redis_db}"
        
        try:
            # RedisDb only accepts db_url parameter
            self.db = RedisDb(
                db_url=redis_url,
            )
            logger.info(f"Initialized Agno Redis storage at {redis_host}:{redis_port}/{redis_db}")
        except Exception as e:
            logger.error(f"Failed to initialize Agno Redis storage: {e}")
            logger.warning("Agent will operate without persistent memory")
            self.db = None
    
    def get_db(self) -> Optional[RedisDb]:
        """Get the Redis database instance."""
        return self.db


# Singleton instance
_agno_storage_instance: Optional[AgnoRedisStorage] = None


def get_agno_storage() -> AgnoRedisStorage:
    """Get or create the Agno Redis storage singleton."""
    global _agno_storage_instance
    if _agno_storage_instance is None:
        _agno_storage_instance = AgnoRedisStorage()
    return _agno_storage_instance


def get_agno_db() -> Optional[RedisDb]:
    """Get the Agno Redis database instance directly."""
    storage = get_agno_storage()
    return storage.get_db()

