"""
User Information Tools
======================
MCP tools for retrieving user profile and beneficiary information.
"""

from typing import List, Dict, Any
import logging

logger = logging.getLogger(__name__)


async def get_user_details_tool(user) -> Dict[str, Any]:
    """
    Get user profile details including email, name, roles, and permissions.
    
    Args:
        user: Authenticated user object
        
    Returns:
        User information dictionary
    """
    logger.info(f"User details request for user_id: {user.user_id}")
    
    try:
        from backend_client import get_backend_client
        backend_client = get_backend_client()
        user_details = await backend_client.get_user_details(user.user_id)
        
        logger.info(f"User details retrieved for user_id: {user.user_id}")
        
        return user_details
        
    except Exception as e:
        logger.error(f"Error retrieving user details: {e}")
        raise ValueError(f"Failed to retrieve user details: {str(e)}")


async def get_beneficiaries_tool(user) -> List[Dict[str, Any]]:
    """
    Get beneficiary contacts for payments.
    
    Args:
        user: Authenticated user object
        
    Returns:
        List of beneficiary contact information
    """
    logger.info(f"Beneficiaries request for user_id: {user.user_id}")
    
    try:
        from backend_client import get_backend_client
        backend_client = get_backend_client()
        beneficiaries = await backend_client.get_beneficiaries(user.user_id)
        
        logger.info(
            f"Beneficiaries retrieved for user_id: {user.user_id}, "
            f"count: {len(beneficiaries)}"
        )
        
        return beneficiaries
        
    except Exception as e:
        logger.error(f"Error retrieving beneficiaries: {e}")
        raise ValueError(f"Failed to retrieve beneficiaries: {str(e)}")

