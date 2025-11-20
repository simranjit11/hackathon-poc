"""
Alert and Reminder Tools
=========================
MCP tools for managing alerts and payment reminders.
"""

from typing import List
import logging

from mcp_server.banking_api import BankingAPI

logger = logging.getLogger(__name__)


async def set_alert_tool(
    user,
    alert_type: str,
    description: str,
    due_date: str = ""
) -> dict:
    """
    Set up a payment alert or reminder.
    
    Args:
        user: Authenticated user object
        alert_type: Type of alert (e.g., 'low_balance', 'payment_due')
        description: Alert description
        due_date: Optional due date for payment reminders
        
    Returns:
        Alert confirmation with details
    """
    logger.info(
        f"Set alert request for user_id: {user.user_id}, "
        f"type: {alert_type}"
    )
    
    try:
        # Query banking API
        banking_api = BankingAPI()
        result = await banking_api.set_alert(
            user.user_id,
            alert_type,
            description,
            due_date
        )
        
        logger.info(
            f"Alert set for user_id: {user.user_id}, "
            f"type: {alert_type}"
        )
        
        return result
        
    except Exception as e:
        logger.error(f"Error setting alert: {e}")
        raise ValueError(f"Failed to set alert: {str(e)}")


async def get_alerts_tool(user) -> List[dict]:
    """
    Get active alerts and reminders for the authenticated user.
    
    Args:
        user: Authenticated user object
        
    Returns:
        List of active alerts
    """
    logger.info(f"Get alerts request for user_id: {user.user_id}")
    
    try:
        # Query banking API
        banking_api = BankingAPI()
        alerts = await banking_api.get_alerts(user.user_id)
        
        logger.info(
            f"Alerts retrieved for user_id: {user.user_id}, "
            f"count: {len(alerts)}"
        )
        
        return alerts
        
    except Exception as e:
        logger.error(f"Error retrieving alerts: {e}")
        raise ValueError(f"Failed to retrieve alerts: {str(e)}")

