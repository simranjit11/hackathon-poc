"""
Loan Information Tools
======================
MCP tools for retrieving loan information.
"""

from typing import List
import logging

from mcp_server.banking_api import BankingAPI
from mcp_server.cache import cache_manager

logger = logging.getLogger(__name__)


async def get_loans_tool(user) -> List[dict]:
    """
    Get loan information for the authenticated user.
    
    Args:
        user: Authenticated user object
        
    Returns:
        List of loan responses with details and payment schedules
    """
    logger.info(f"Loan request for user_id: {user.user_id}")
    
    try:
        # Check cache
        cache_key = f"loans:{user.user_id}"
        cached_result = await cache_manager.get(cache_key)
        if cached_result:
            logger.info(f"Returning cached loans for user_id: {user.user_id}")
            return cached_result
        
        # Query banking API
        banking_api = BankingAPI()
        loans = await banking_api.get_loans(user.user_id)
        
        # Cache results (10 minute TTL)
        await cache_manager.set(cache_key, loans, ttl=600)
        
        logger.info(
            f"Loans retrieved for user_id: {user.user_id}, "
            f"count: {len(loans)}"
        )
        
        return loans
        
    except Exception as e:
        logger.error(f"Error retrieving loans: {e}")
        raise ValueError(f"Failed to retrieve loan information: {str(e)}")

