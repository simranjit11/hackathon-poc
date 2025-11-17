"""
Database connection pool manager for PostgreSQL.
"""

import asyncpg
import logging
from typing import Optional

from mcp_server.config import settings

logger = logging.getLogger(__name__)

_pool: Optional[asyncpg.Pool] = None


async def get_pool() -> asyncpg.Pool:
    """
    Get or create database connection pool.
    Creates pool lazily in the current event loop context.
    
    Returns:
        AsyncPG connection pool
    """
    global _pool
    
    # Create pool lazily - will be created in the current event loop context
    # Note: asyncpg pools are tied to the event loop they're created in
    if _pool is None or _pool.is_closing():
        logger.info("Creating database connection pool...")
        try:
            _pool = await asyncpg.create_pool(
                settings.DATABASE_URL,
                min_size=settings.DATABASE_POOL_MIN_SIZE,
                max_size=settings.DATABASE_POOL_MAX_SIZE,
                command_timeout=60
            )
            logger.info("Database connection pool created")
        except Exception as e:
            logger.error(f"Failed to create database connection pool: {e}")
            raise
    
    return _pool


async def close_pool() -> None:
    """Close database connection pool."""
    global _pool
    
    if _pool is not None:
        logger.info("Closing database connection pool...")
        try:
            await _pool.close()
        except Exception as e:
            logger.warning(f"Error closing pool: {e}")
        finally:
            _pool = None
        logger.info("Database connection pool closed")
