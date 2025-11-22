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
            "get_reminders": ["read"],
            "get_interest_rates": ["read"],
            "get_current_date_time": ["read"],
            "get_user_details": ["read"],  # Get user profile information
            "get_transfer_contacts": ["read"],  # Get beneficiaries/contacts
            "make_payment_with_elicitation": ["transact"],
            "create_reminder": ["configure"],
            "update_reminder": ["configure"],
            "delete_reminder": ["configure"],
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
        # Get required scope for this tool
        scopes = self.scope_map.get(tool_name, ["read"])
        
        # Remove jwt_token if present (we'll add our own)
        kwargs.pop("jwt_token", None)
        
        # Extract parameters from nested structures if LLM sends them that way
        # Sometimes the LLM sends {'kwargs': {'param1': 'value1', ...}} instead of flat params
        extracted_kwargs = {}
        for key, value in kwargs.items():
            if key == "kwargs" and isinstance(value, dict):
                # If there's a 'kwargs' key with a dict value, extract those params
                extracted_kwargs.update(value)
            elif isinstance(value, dict) and len(value) == 1:
                # If a param value is a single-item dict like {'date': '2025-12-20'},
                # extract the inner value
                inner_key, inner_value = next(iter(value.items()))
                extracted_kwargs[key] = inner_value
            else:
                extracted_kwargs[key] = value
        
        # Filter out None values, empty strings, and empty dicts to avoid validation errors
        # FastMCP is strict about unexpected keyword arguments
        filtered_kwargs = {
            k: v for k, v in extracted_kwargs.items()
            if v is not None and v != "" and not (isinstance(v, dict) and len(v) == 0)
        }
        
        # Call via MCP client which handles JWT generation and HTTP calls
        try:
            result = await self.mcp_client._call_mcp_tool(
                tool_name,
                self.user_id,
                self.session_id,
                scopes,
                email=self.email,
                **filtered_kwargs
            )
            return result
        except Exception as e:
            logger.error(f"MCP Tool {tool_name} failed: {e}")
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
                "description": "Get account balances for the authenticated user. Optionally filter by account type (checking, savings, credit_card). Returns list of accounts with balances and account_id (use account_id for create_reminder).",
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
                "name": "get_reminders",
                "description": "Get payment reminders for the authenticated user. Optional filters: is_completed (true/false), scheduled_date_from (date string), scheduled_date_to (date string). Returns list of reminders with status, amount, recipient, and scheduled date.",
                "func": self._create_tool_func_with_params("get_reminders"),
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
                "name": "make_payment_with_elicitation",
                "description": "Make a payment or transfer funds with user confirmation (OTP/approval). Use this for all payments. Requires from_account (source account), to_account (recipient account number), amount (payment amount), and optional description. Returns elicitation request for user confirmation.",
                "func": self._create_tool_func_with_params("make_payment_with_elicitation"),
            },
            {
                "name": "create_reminder",
                "description": "Create a payment reminder for a future scheduled payment. REQUIRED: scheduled_date, amount (number), recipient (string), account_id (string - get this from get_balance tool). OPTIONAL: description (string), beneficiary_id (string), beneficiary_nickname (string). IMPORTANT: All parameters must be primitive values (strings, numbers), NOT objects or dictionaries. Returns reminder confirmation with ID.",
                "func": self._create_tool_func_with_params("create_reminder"),
            },
            {
                "name": "update_reminder",
                "description": "Update an existing payment reminder. REQUIRED: reminder_id (string). OPTIONAL: scheduled_date (date string), amount (number), recipient (string), description (string), account_id (string), is_completed (true/false). Returns updated reminder details.",
                "func": self._create_tool_func_with_params("update_reminder"),
            },
            {
                "name": "delete_reminder",
                "description": "Delete a payment reminder. REQUIRED: reminder_id (string). Returns deletion confirmation.",
                "func": self._create_tool_func_with_params("delete_reminder"),
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
        
        return tools
    
    def _create_tool_func_no_params(self, tool_name: str):
        """
        Create an async function for tools that take no parameters.
        Accepts **kwargs to be compatible with Agno's function calling, but ignores them.
        """
        async def tool_func(**kwargs: Any) -> Any:
            """Tool function that calls MCP server via HTTP with JWT."""
            # Ignore kwargs for no-param tools, but accept them to avoid Pydantic validation errors
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


def create_agno_mcp_tools(user_id: str, session_id: str, email: Optional[str] = None):
    """
    Create MCP tools wrapper for Agno.
    
    Args:
        user_id: User identifier
        session_id: Session/room identifier
        email: User email address (optional but recommended)
        
    Returns:
        AuthenticatedMCPTools instance
    """
    return AuthenticatedMCPTools(user_id, session_id, email=email)