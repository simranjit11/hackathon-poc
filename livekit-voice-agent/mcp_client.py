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
        
        # Debug log for JWT secret (masked)
        masked_secret = f"{self.jwt_secret[:4]}...{self.jwt_secret[-4:]}" if len(self.jwt_secret) > 8 else "***"
        logger.info(f"MCP Client initialized with JWT Secret: {masked_secret}, Issuer: {self.jwt_issuer}")
        
        # HTTP client with timeout and redirect following
        # Configure with proper connection limits and keep-alive to prevent premature disconnections
        self.client = httpx.AsyncClient(
            timeout=httpx.Timeout(30.0, connect=10.0, read=30.0, write=10.0, pool=5.0),
            base_url=self.mcp_url,
            follow_redirects=True,  # Follow redirects (e.g., /mcp/ -> /mcp)
            limits=httpx.Limits(
                max_keepalive_connections=10,
                max_connections=20,
                keepalive_expiry=30.0
            ),
            http2=False  # Disable HTTP/2 to avoid streaming issues
        )
    
    def _generate_jwt(
        self,
        user_id: str,
        scopes: List[str],
        session_id: str,
        email: Optional[str] = None
    ) -> str:
        """
        Generate short-lived JWT token for MCP server.
        
        Args:
            user_id: User identifier
            scopes: List of scopes (e.g., ['read'], ['transact'], ['configure'])
            session_id: Session/room identifier
            email: User email address (optional but recommended)
            
        Returns:
            JWT token string
        """
        now = datetime.utcnow()
        payload = {
            "iss": self.jwt_issuer,
            "sub": user_id,
            "scopes": scopes,  # Keep for MCP server compatibility
            "permissions": scopes,  # Map scopes to permissions for Next.js API
            "roles": ["customer"],  # Default role for Next.js API
            "session_id": session_id,
            "iat": now,
            "exp": now + timedelta(minutes=5),  # 5 minute expiration
            "jti": f"{user_id}-{now.timestamp()}"
        }
        
        # If user_id is in UUID format (contains hyphens), it's likely a real user
        # If it's numeric (like "12345"), it's a legacy/test user
        # We'll include both sub and user_id claim for compatibility
        if "-" in str(user_id):
             payload["user_id"] = user_id
        
        # Include email if provided (required by Next.js API)
        if email:
            payload["email"] = email
        else:
            # Fallback email if not provided (Next.js requires email)
            payload["email"] = f"user_{user_id}@example.com"

        token = jwt.encode(
            payload,
            self.jwt_secret,
            algorithm=self.jwt_algorithm
        )
        
        logger.debug(f"Generated JWT for user_id: {user_id}, email: {payload.get('email')}, scopes: {scopes}, permissions: {scopes}")
        return token
    
    async def _call_mcp_tool(
        self,
        tool_name: str,
        user_id: str,
        session_id: str,
        scopes: List[str],
        email: Optional[str] = None,
        **kwargs
    ) -> Any:
        """
        Call an MCP tool via JSON-RPC over HTTP (FastMCP protocol).
        
        Args:
            tool_name: Name of the MCP tool to call
            user_id: User identifier
            session_id: Session/room identifier
            scopes: Required scopes for this operation
            email: User email address (optional but recommended)
            **kwargs: Tool-specific parameters
            
        Returns:
            Tool response
        """
        jwt_token = self._generate_jwt(user_id, scopes, session_id, email=email)
        
        # Build tool arguments
        # Include jwt_token in arguments for tools that require it as a parameter
        # Also send in headers for tools that read from headers
        tool_arguments = {
            "jwt_token": jwt_token,
            **kwargs
        }
        
        # FastMCP uses JSON-RPC 2.0 protocol
        # POST to base MCP path with JSON-RPC request
        jsonrpc_request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": tool_name,
                "arguments": tool_arguments
            }
        }
        
        try:
            # FastMCP expects JSON-RPC requests at the base MCP path
            # JWT token should be in Authorization header (some tools read from headers)
            # Use empty string to avoid trailing slash redirect issues
            # httpx will automatically follow redirects if needed
            headers = {
                "Content-Type": "application/json",
                "Accept": "application/json",
                "Authorization": f"Bearer {jwt_token}",
                "X-JWT-Token": jwt_token  # Fallback header
            }
            
            # Make request and ensure full response is consumed
            # This prevents the connection from closing before the server finishes writing
            response = await self.client.post(
                "",
                json=jsonrpc_request,
                headers=headers
            )
            
            # Log response details for debugging
            logger.debug(f"MCP tool call response status: {response.status_code}")
            logger.debug(f"MCP tool call response headers: {dict(response.headers)}")
            
            response.raise_for_status()
            
            # Read the full response content
            # Using .text property reads the entire response body synchronously
            # This ensures all data is received before the connection can be closed
            # The response object will be automatically cleaned up after we're done
            response_text = response.text
            
            # Parse JSON-RPC response
            try:
                jsonrpc_response = json.loads(response_text)
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse JSON response: {e}, response text: {response_text[:200]}")
                raise ValueError(f"Invalid JSON response from MCP server: {e}")
            
            # Check for JSON-RPC errors
            if "error" in jsonrpc_response:
                error_msg = jsonrpc_response["error"].get("message", "Unknown error")
                error_code = jsonrpc_response["error"].get("code", "Unknown")
                logger.error(f"JSON-RPC error calling {tool_name}: [{error_code}] {error_msg}")
                raise ValueError(f"Failed to call {tool_name}: [{error_code}] {error_msg}")
            
            # Return the result from JSON-RPC response
            return jsonrpc_response.get("result")
            
        except httpx.HTTPStatusError as e:
            # Log response body for debugging 406 errors
            try:
                error_body = e.response.text
                logger.error(f"MCP tool call failed with status {e.response.status_code}: {error_body}")
            except Exception:
                pass
            logger.error(f"MCP tool call failed: {e}")
            raise ValueError(f"Failed to call {tool_name}: {str(e)}")
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

