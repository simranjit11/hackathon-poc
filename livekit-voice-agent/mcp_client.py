"""
MCP Client for LiveKit Voice Agent
====================================
Client for calling MCP server tools with JWT authentication.
"""

import os
import httpx
import json
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from jose import jwt
from dotenv import load_dotenv
import logging

load_dotenv()

logger = logging.getLogger(__name__)


class MCPClient:
    """Client for calling MCP server tools."""
    
    def __init__(self):
        """Initialize MCP client with configuration."""
        self.mcp_url = os.getenv("MCP_SERVER_URL", "http://localhost:8001/mcp")
        self.jwt_secret = os.getenv("MCP_JWT_SECRET_KEY", "your-secret-key-change-in-production")
        self.jwt_issuer = os.getenv("MCP_JWT_ISSUER", "orchestrator")
        self.jwt_algorithm = os.getenv("MCP_JWT_ALGORITHM", "HS256")
        
        # HTTP client with timeout
        self.client = httpx.AsyncClient(
            timeout=30.0,
            base_url=self.mcp_url
        )
    
    def _generate_jwt(
        self,
        user_id: str,
        scopes: List[str],
        session_id: str
    ) -> str:
        """
        Generate short-lived JWT token for MCP server.
        
        Args:
            user_id: User identifier
            scopes: List of scopes (e.g., ['read'], ['transact'], ['configure'])
            session_id: Session/room identifier
            
        Returns:
            JWT token string
        """
        now = datetime.utcnow()
        payload = {
            "iss": self.jwt_issuer,
            "sub": user_id,
            "scopes": scopes,
            "session_id": session_id,
            "iat": now,
            "exp": now + timedelta(minutes=5),  # 5 minute expiration
            "jti": f"{user_id}-{now.timestamp()}"
        }
        
        token = jwt.encode(
            payload,
            self.jwt_secret,
            algorithm=self.jwt_algorithm
        )
        
        logger.debug(f"Generated JWT for user_id: {user_id}, scopes: {scopes}")
        return token
    
    async def _call_mcp_tool(
        self,
        tool_name: str,
        user_id: str,
        session_id: str,
        scopes: List[str],
        **kwargs
    ) -> Any:
        """
        Call an MCP tool via HTTP.
        
        Args:
            tool_name: Name of the MCP tool to call
            user_id: User identifier
            session_id: Session/room identifier
            scopes: Required scopes for this operation
            **kwargs: Tool-specific parameters
            
        Returns:
            Tool response
        """
        jwt_token = self._generate_jwt(user_id, scopes, session_id)
        
        # Add jwt_token to kwargs
        params = {
            "jwt_token": jwt_token,
            **kwargs
        }
        
        try:
            # MCP tools are called via POST to /tools/{tool_name}
            response = await self.client.post(
                f"/tools/{tool_name}",
                json=params
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            logger.error(f"MCP tool call failed: {e}")
            raise ValueError(f"Failed to call {tool_name}: {str(e)}")
    
    async def get_balance(
        self,
        user_id: str,
        session_id: str,
        account_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get account balances."""
        return await self._call_mcp_tool(
            "get_balance",
            user_id,
            session_id,
            ["read"],
            account_type=account_type
        )
    
    async def get_transactions(
        self,
        user_id: str,
        session_id: str,
        account_type: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Get transaction history."""
        return await self._call_mcp_tool(
            "get_transactions",
            user_id,
            session_id,
            ["read"],
            account_type=account_type,
            start_date=start_date,
            end_date=end_date,
            limit=limit
        )
    
    async def get_loans(
        self,
        user_id: str,
        session_id: str
    ) -> List[Dict[str, Any]]:
        """Get loan information."""
        return await self._call_mcp_tool(
            "get_loans",
            user_id,
            session_id,
            ["read"]
        )
    
    async def make_payment(
        self,
        user_id: str,
        session_id: str,
        from_account: str,
        to_account: str,
        amount: float,
        description: str = ""
    ) -> Dict[str, Any]:
        """Make a payment or transfer."""
        return await self._call_mcp_tool(
            "make_payment",
            user_id,
            session_id,
            ["transact"],
            from_account=from_account,
            to_account=to_account,
            amount=amount,
            description=description
        )
    
    async def get_credit_limit(
        self,
        user_id: str,
        session_id: str
    ) -> Dict[str, Any]:
        """Get credit card limits."""
        return await self._call_mcp_tool(
            "get_credit_limit",
            user_id,
            session_id,
            ["read"]
        )
    
    async def set_alert(
        self,
        user_id: str,
        session_id: str,
        alert_type: str,
        description: str,
        due_date: str = ""
    ) -> Dict[str, Any]:
        """Set up payment reminder or alert."""
        return await self._call_mcp_tool(
            "set_alert",
            user_id,
            session_id,
            ["configure"],
            alert_type=alert_type,
            description=description,
            due_date=due_date
        )
    
    async def get_alerts(
        self,
        user_id: str,
        session_id: str
    ) -> List[Dict[str, Any]]:
        """Get active alerts."""
        return await self._call_mcp_tool(
            "get_alerts",
            user_id,
            session_id,
            ["read"]
        )
    
    async def get_interest_rates(
        self,
        user_id: str,
        session_id: str
    ) -> str:
        """Get current interest rates."""
        return await self._call_mcp_tool(
            "get_interest_rates",
            user_id,
            session_id,
            ["read"]
        )
    
    async def get_current_date_time(
        self,
        user_id: str,
        session_id: str
    ) -> str:
        """Get current date and time."""
        return await self._call_mcp_tool(
            "get_current_date_time",
            user_id,
            session_id,
            ["read"]
        )
    
    async def close(self):
        """Close HTTP client."""
        await self.client.aclose()


# Global MCP client instance
_mcp_client: Optional[MCPClient] = None


def get_mcp_client() -> MCPClient:
    """Get or create the global MCP client instance."""
    global _mcp_client
    if _mcp_client is None:
        _mcp_client = MCPClient()
    return _mcp_client

