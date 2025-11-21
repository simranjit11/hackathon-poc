"""
Agno MCP Integration
=====================
Creates Function objects for Agno that call MCP server via HTTP with JWT authentication.
Since we need custom JWT injection, we create Function objects directly instead of using
Agno's MCPTools discovery (which requires connection and may fail).
"""

import os
import logging
from typing import Optional, List, Dict, Any
from agno.tools.function import Function
from mcp_client import get_mcp_client

logger = logging.getLogger(__name__)


class AuthenticatedMCPTools:
    """
    MCP tools wrapper for Agno.
    Creates Function objects that call MCP server via HTTP with JWT authentication.
    Uses Function.from_callable() to convert async functions into Agno Function objects.
    """
    
    def __init__(self, user_id: str, session_id: str, email: Optional[str] = None, mcp_url: Optional[str] = None):
        """
        Initialize authenticated MCP tools.
        
        Args:
            user_id: User identifier for JWT generation
            session_id: Session/room identifier for JWT generation
            email: User email address for JWT generation (optional but recommended)
            mcp_url: MCP server URL (defaults to env var, kept for compatibility)
        """
        self.user_id = user_id
        self.session_id = session_id
        self.email = email
        self.mcp_client = get_mcp_client()
        
        # Scope mapping for JWT generation
        self.scope_map = {
            "get_balance": ["read"],
            "get_transactions": ["read"],
            "get_loans": ["read"],
            "get_credit_limit": ["read"],
            "get_alerts": ["read"],
            "get_interest_rates": ["read"],
            "get_current_date_time": ["read"],
            "get_user_details": ["read"],  # Get user profile information
            "get_transfer_contacts": ["read"],  # Get beneficiaries/contacts
            "initiate_payment": ["transact"],  # Initiate payment with elicitation
            "set_alert": ["configure"],
        }
    
    async def _call_tool(self, tool_name: str, **kwargs) -> Any:
        """
        Call MCP tool via HTTP with JWT authentication.
        
        Args:
            tool_name: Name of the tool to call
            **kwargs: Tool parameters
            
        Returns:
            Tool response
        """
        logger.info(f"🔧 MCP Tool called: {tool_name} with params: {kwargs}")
        
        # Get required scope for this tool
        scopes = self.scope_map.get(tool_name, ["read"])
        
        # Remove jwt_token if present (we'll add our own)
        kwargs.pop("jwt_token", None)
        
        # Call via MCP client which handles JWT generation and HTTP calls
        try:
            result = await self.mcp_client._call_mcp_tool(
                tool_name,
                self.user_id,
                self.session_id,
                scopes,
                email=self.email,
                **kwargs
            )
            logger.info(f"✅ MCP Tool {tool_name} succeeded")
            return result
        except Exception as e:
            logger.error(f"❌ MCP Tool {tool_name} failed: {e}")
            raise
    
    def get_tools(self) -> List[Function]:
        """
        Get list of Agno Function objects for all available MCP tools.
        These functions will call our _call_tool method which uses HTTP with JWT.
        
        Returns:
            List of Function objects that can be used by AgnoAgent
        """
        tools = []
        
        # Define all available tools with descriptions and parameter types
        tool_definitions = [
            {
                "name": "get_balance",
                "description": "Get account balances for the authenticated user. Optionally filter by account type (checking, savings, credit_card). Returns list of accounts with balances.",
                "func": self._create_tool_func_with_params("get_balance"),
            },
            {
                "name": "get_transactions",
                "description": "Get transaction history for the authenticated user. Can filter by account_type (checking, savings, credit_card), start_date (YYYY-MM-DD), end_date (YYYY-MM-DD), and limit (default: 10, max: 100). Returns list of recent transactions.",
                "func": self._create_tool_func_with_params("get_transactions"),
            },
            {
                "name": "get_loans",
                "description": "Get loan information for the authenticated user including balance, interest rate, monthly payment, and remaining term. Returns list of loans.",
                "func": self._create_tool_func_no_params("get_loans"),
            },
            {
                "name": "get_credit_limit",
                "description": "Get credit card limits and available credit for the authenticated user. Returns credit limit information.",
                "func": self._create_tool_func_no_params("get_credit_limit"),
            },
            {
                "name": "get_alerts",
                "description": "Get active payment alerts and reminders for the authenticated user. Returns list of alerts.",
                "func": self._create_tool_func_no_params("get_alerts"),
            },
            {
                "name": "get_interest_rates",
                "description": "Get current interest rates for various banking products (deposit accounts, credit products, mortgages). Returns formatted interest rates information.",
                "func": self._create_tool_func_no_params("get_interest_rates"),
            },
            {
                "name": "get_current_date_time",
                "description": "Get the current date and time. Returns formatted date/time string.",
                "func": self._create_tool_func_no_params("get_current_date_time"),
            },
            {
                "name": "get_user_details",
                "description": "Get user profile details including email, name, roles, and permissions. Returns user information dictionary.",
                "func": self._create_tool_func_no_params("get_user_details"),
            },
            {
                "name": "get_transfer_contacts",
                "description": "Get list of saved contacts/beneficiaries for transfers. Useful for resolving names like 'Pay Bob' to actual payment details. Returns list of beneficiary dictionaries with nickname and payment information.",
                "func": self._create_tool_func_no_params("get_transfer_contacts"),
            },
            {
                "name": "initiate_payment",
                "description": "Initiate a payment or transfer funds. Triggers elicitation flow requiring user confirmation via OTP. CRITICAL: to_account MUST be the recipient's UPI ID or account number (e.g., 'john@okicici.com'), NOT their name. ALWAYS call get_transfer_contacts first to resolve names to payment addresses. REQUIRED: to_account (UPI ID/account number from contact's paymentAddress field), amount (number). OPTIONAL: from_account (e.g., 'checking', 'savings'), description. Returns elicitation request with payment session details.",
                "func": self._create_tool_func_with_params("initiate_payment"),
            },
            {
                "name": "set_alert",
                "description": "Set up a payment alert or reminder. Requires alert_type (e.g., 'low_balance', 'payment_due'), amount (threshold amount), and optional description. Returns alert confirmation.",
                "func": self._create_tool_func_with_params("set_alert"),
            },
        ]
        
        # Create Function objects for Agno using Function.from_callable()
        for tool_def in tool_definitions:
            # Create a properly named function for Agno to introspect
            tool_func = tool_def["func"]
            tool_func.__name__ = tool_def["name"]
            tool_func.__doc__ = tool_def["description"]
            
            # Use Function.from_callable() to create Function object
            # This automatically infers JSON schema from function signature
            function = Function.from_callable(tool_func, name=tool_def["name"], strict=False)
            function.description = tool_def["description"]
            tools.append(function)
        
        logger.info(f"Created {len(tools)} MCP tools for Agno agent")
        return tools
    
    def _create_tool_func_no_params(self, tool_name: str):
        """
        Create an async function for tools that take no parameters.
        """
        async def tool_func() -> Any:
            """Tool function that calls MCP server via HTTP with JWT."""
            return await self._call_tool(tool_name)
        
        return tool_func
    
    def _create_tool_func_with_params(self, tool_name: str):
        """
        Create an async function for tools that accept parameters.
        Uses **kwargs to accept any parameters that will be passed to MCP.
        """
        async def tool_func(**kwargs: Any) -> Any:
            """Tool function that calls MCP server via HTTP with JWT."""
            return await self._call_tool(tool_name, **kwargs)
        
        return tool_func


def create_agno_mcp_tools(user_id: str, session_id: str):
    """
    Create MCP tools wrapper for Agno.
    
    Args:
        user_id: User identifier
        session_id: Session/room identifier
        
    Returns:
        AuthenticatedMCPTools instance
    """
    return AuthenticatedMCPTools(user_id, session_id)
