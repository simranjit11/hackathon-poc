"""
Payment and Transfer Tools
===========================
MCP tools for making payments and transfers.
"""

import logging

from mcp_server.banking_api import BankingAPI

logger = logging.getLogger(__name__)


async def make_payment_tool(
    user,
    from_account: str,
    to_account: str,
    amount: float,
    description: str = ""
) -> dict:
    """
    Make a payment or transfer between accounts.
    
    Args:
        user: Authenticated user object
        from_account: Source account type ('checking', 'savings')
        to_account: Destination account or payee name
        amount: Amount to transfer
        description: Optional description for the transaction
        
    Returns:
        Payment confirmation with details
    """
    logger.info(
        f"Payment request for user_id: {user.user_id}, "
        f"from: {from_account}, to: {to_account}, amount: {amount}"
    )
    
    try:
        # Query banking API
        banking_api = BankingAPI()
        result = await banking_api.make_payment(
            user.user_id,
            from_account,
            to_account,
            amount,
            description
        )
        
        logger.info(
            f"Payment successful for user_id: {user.user_id}, "
            f"confirmation: {result['confirmation_number']}"
        )
        
        return result
        
    except ValueError as e:
        logger.warning(f"Payment error: {e}")
        raise ValueError(f"Payment failed: {str(e)}")
    except Exception as e:
        logger.error(f"Error processing payment: {e}")
        raise ValueError(f"Failed to process payment: {str(e)}")

