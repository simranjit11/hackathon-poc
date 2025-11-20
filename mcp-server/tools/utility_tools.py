"""
Utility Tools
=============
MCP tools for general utility functions (interest rates, date/time, etc.).
"""

from datetime import datetime
import logging

from mcp_server.banking_api import BankingAPI

logger = logging.getLogger(__name__)


async def get_interest_rates_tool(user) -> str:
    """
    Get current interest rates for various banking products.
    
    Args:
        user: Authenticated user object
        
    Returns:
        Formatted interest rates information
    """
    logger.info(f"Interest rates request for user_id: {user.user_id}")
    
    try:
        # Query banking API
        banking_api = BankingAPI()
        rates = await banking_api.get_interest_rates(user.user_id)
        
        logger.info(f"Interest rates retrieved for user_id: {user.user_id}")
        
        return rates
        
    except Exception as e:
        logger.error(f"Error retrieving interest rates: {e}")
        raise ValueError(f"Failed to retrieve interest rates: {str(e)}")


async def get_current_date_time_tool(user) -> str:
    """
    Get current date and time.
    
    Args:
        user: Authenticated user object (for logging purposes)
        
    Returns:
        Formatted current date and time
    """
    logger.info(f"Date/time request for user_id: {user.user_id}")
    
    try:
        now = datetime.now()
        formatted = now.strftime("%A, %B %d, %Y at %I:%M %p")
        
        logger.info(f"Current date/time retrieved for user_id: {user.user_id}")
        
        return f"The current date and time is {formatted}"
        
    except Exception as e:
        logger.error(f"Error getting date/time: {e}")
        raise ValueError(f"Failed to get current date and time: {str(e)}")

