"""
Utility Tools
=============
MCP tools for general utility functions (date/time, etc.).
"""

from datetime import datetime
import logging

logger = logging.getLogger(__name__)


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

