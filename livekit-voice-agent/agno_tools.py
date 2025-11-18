"""
Agno MCP Integration
=====================
Uses Agno's MCPTools to connect directly to MCP server.
Tools are automatically discovered - no manual tool definitions needed.
JWT authentication is handled via MCP client wrapper.
"""

import os
from typing import Optional
from agno.tools.mcp import MCPTools
from mcp_client import get_mcp_client


class AuthenticatedMCPTools(MCPTools):
    """
    Wraps Agno's MCPTools to inject JWT authentication.
    Tools are automatically discovered from MCP server - no manual definitions!
    """
    
    def __init__(self, user_id: str, session_id: str, mcp_url: Optional[str] = None):
        """
        Initialize authenticated MCP tools.
        Connects to MCP server and discovers tools automatically.
        
        Args:
            user_id: User identifier for JWT generation
            session_id: Session/room identifier for JWT generation
            mcp_url: MCP server URL (defaults to env var)
        """
        self.user_id = user_id
        self.session_id = session_id
        self.mcp_client = get_mcp_client()
        
        # Get MCP server URL
        mcp_url = mcp_url or os.getenv("MCP_SERVER_URL", "http://localhost:8001/mcp")
        
        # Initialize Agno's MCPTools - it will discover tools from server
        super().__init__(url=mcp_url)
        
        # Scope mapping for JWT generation
        self.scope_map = {
            "get_balance": ["read"],
            "get_transactions": ["read"],
            "get_loans": ["read"],
            "get_credit_limit": ["read"],
            "get_alerts": ["read"],
            "get_interest_rates": ["read"],
            "get_current_date_time": ["read"],
            "make_payment": ["transact"],
            "set_alert": ["configure"],
        }
    
    async def _call_tool(self, tool_name: str, **kwargs):
        """
        Override tool calls to inject JWT authentication.
        This intercepts Agno's tool calls and adds JWT token.
        
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
        
        # Call via MCP client which handles JWT generation
        return await self.mcp_client._call_mcp_tool(
            tool_name,
            self.user_id,
            self.session_id,
            scopes,
            **kwargs
        )


def create_agno_mcp_tools(user_id: str, session_id: str):
    """
    Create Agno MCPTools instance that connects to MCP server.
    Tools are automatically discovered from the MCP server - no manual definitions!
    
    Args:
        user_id: User identifier
        session_id: Session/room identifier
        
    Returns:
        AuthenticatedMCPTools instance (wraps Agno's MCPTools)
    """
    return AuthenticatedMCPTools(user_id, session_id)

