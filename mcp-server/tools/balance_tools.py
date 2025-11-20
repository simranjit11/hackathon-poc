"""
Balance and Account Information Tools
======================================
MCP tools for retrieving account balances and information.
"""

from typing import Optional, List
import logging

from mcp_server.banking_api import BankingAPI
from mcp_server.cache import cache_manager
from mcp_server.masking import mask_account_number

logger = logging.getLogger(__name__)


async def get_balance_tool(
    user,
    account_type: Optional[str] = None
) -> List[dict]:
    """
    Get account balances for the authenticated user.
    
    Args:
        user: Authenticated user object
        account_type: Optional account type filter (checking, savings, credit_card)
        
    Returns:
        List of balance responses for all account types
    """
    logger.info(f"Balance request for user_id: {user.user_id}")
    
    try:
        # Check cache
        cache_key = f"balance:{user.user_id}:{account_type or 'all'}"
        cached_result = await cache_manager.get(cache_key)
        if cached_result:
            logger.info(f"Returning cached balance for user_id: {user.user_id}")
            return cached_result
        
        # Query banking API
        banking_api = BankingAPI()
        accounts = await banking_api.get_accounts(user.user_id)
        
        # Filter by account_type if specified
        if account_type:
            accounts = [
                acc for acc in accounts
                if acc.get("type", "").lower() == account_type.lower()
            ]
        
        # Build response with masking
        balances = []
        for account in accounts:
            acc_type = account.get("type", "unknown")
            acc_number = account.get("account_number", "")
            balance = account.get("balance", 0.0)
            
            response = {
                "account_type": acc_type,
                "account_number": mask_account_number(acc_number),
                "balance": balance,
                "currency": "USD"
            }
            
            # Add credit card specific fields
            if acc_type == "credit_card":
                response["credit_limit"] = account.get("limit", 0.0)
                response["available_credit"] = account.get("limit", 0.0) - balance
            
            balances.append(response)
        
        # Cache results (5 minute TTL)
        await cache_manager.set(cache_key, balances, ttl=300)
        
        logger.info(
            f"Balance retrieved for user_id: {user.user_id}, "
            f"accounts: {len(balances)}"
        )
        
        return balances
        
    except Exception as e:
        logger.error(f"Error retrieving balance: {e}")
        raise ValueError(f"Failed to retrieve account balances: {str(e)}")


async def get_credit_limit_tool(user) -> dict:
    """
    Get credit card limits for the authenticated user.
    
    Args:
        user: Authenticated user object
        
    Returns:
        Credit limit information
    """
    logger.info(f"Credit limit request for user_id: {user.user_id}")
    
    try:
        # Check cache
        cache_key = f"credit_limit:{user.user_id}"
        cached_result = await cache_manager.get(cache_key)
        if cached_result:
            logger.info(f"Returning cached credit limit for user_id: {user.user_id}")
            return cached_result
        
        # Query banking API
        banking_api = BankingAPI()
        accounts = await banking_api.get_accounts(user.user_id)
        
        # Find credit card account
        credit_accounts = [
            acc for acc in accounts 
            if acc.get("type") == "credit_card"
        ]
        
        if not credit_accounts:
            return {
                "message": "No credit card account found",
                "has_credit_card": False
            }
        
        # Get first credit card (in production, might need to handle multiple)
        credit_account = credit_accounts[0]
        
        result = {
            "account_number": mask_account_number(credit_account.get("account_number", "")),
            "credit_limit": credit_account.get("limit", 0.0),
            "current_balance": credit_account.get("balance", 0.0),
            "available_credit": credit_account.get("limit", 0.0) - credit_account.get("balance", 0.0),
            "currency": "USD"
        }
        
        # Cache results (5 minute TTL)
        await cache_manager.set(cache_key, result, ttl=300)
        
        logger.info(
            f"Credit limit retrieved for user_id: {user.user_id}, "
            f"limit: {result['credit_limit']}"
        )
        
        return result
        
    except Exception as e:
        logger.error(f"Error retrieving credit limit: {e}")
        raise ValueError(f"Failed to retrieve credit limit: {str(e)}")

