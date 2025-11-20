"""
Transaction History Tools
=========================
MCP tools for retrieving transaction history.
"""

from typing import Optional, List
import logging

from mcp_server.banking_api import BankingAPI
from mcp_server.cache import cache_manager
from mcp_server.masking import mask_account_number, mask_merchant_info

logger = logging.getLogger(__name__)


async def get_transactions_tool(
    user,
    account_type: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    limit: int = 10
) -> List[dict]:
    """
    Get transaction history for the authenticated user.
    
    Args:
        user: Authenticated user object
        account_type: Optional account type filter
        start_date: Optional start date filter (YYYY-MM-DD)
        end_date: Optional end date filter (YYYY-MM-DD)
        limit: Maximum number of transactions (default: 10, max: 100)
        
    Returns:
        List of transaction responses, sorted by date (most recent first)
    """
    logger.info(
        f"Transaction request for user_id: {user.user_id}, "
        f"limit: {limit}"
    )
    
    try:
        # Validate limit
        limit = max(1, min(100, limit))
        
        # Build cache key
        cache_key = (
            f"transactions:{user.user_id}:"
            f"{account_type or 'all'}:"
            f"{start_date or 'none'}:"
            f"{end_date or 'none'}:"
            f"{limit}"
        )
        
        # Check cache
        cached_result = await cache_manager.get(cache_key)
        if cached_result:
            logger.info(f"Returning cached transactions for user_id: {user.user_id}")
            return cached_result
        
        # Query banking API
        banking_api = BankingAPI()
        transactions = await banking_api.get_transactions(
            user.user_id,
            account_type=account_type,
            start_date=start_date,
            end_date=end_date,
            limit=limit
        )
        
        # Build response with masking
        responses = []
        for txn in transactions:
            response = {
                "date": txn.get("date", ""),
                "description": mask_merchant_info(txn.get("description", "")),
                "amount": txn.get("amount", 0.0),
                "type": txn.get("type", "debit"),
                "account_number": mask_account_number(
                    txn.get("account_number", "")
                )
            }
            responses.append(response)
        
        # Sort by date (most recent first)
        responses.sort(key=lambda x: x["date"], reverse=True)
        
        # Cache results (2 minute TTL)
        await cache_manager.set(cache_key, responses, ttl=120)
        
        logger.info(
            f"Transactions retrieved for user_id: {user.user_id}, "
            f"count: {len(responses)}"
        )
        
        return responses
        
    except Exception as e:
        logger.error(f"Error retrieving transactions: {e}")
        raise ValueError(f"Failed to retrieve transactions: {str(e)}")

