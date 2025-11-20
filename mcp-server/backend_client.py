"""
Backend API Client for MCP Server
==================================
Client for server-to-server communication with backend API.
Uses API key authentication for secure backend-to-backend calls.
"""

import os
import httpx
import logging
from typing import Optional, Dict, Any, List

logger = logging.getLogger(__name__)


class BackendAPIClient:
    """
    Client for calling backend API endpoints from MCP server.
    Uses API key authentication for server-to-server communication.
    """
    
    def __init__(
        self,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None
    ):
        """
        Initialize backend API client.
        
        Args:
            base_url: Backend API base URL (defaults to env var)
            api_key: API key for authentication (defaults to env var)
        """
        self.base_url = base_url or os.getenv(
            "BACKEND_API_URL",
            "http://localhost:3000"
        )
        self.api_key = api_key or os.getenv("INTERNAL_API_KEY")
        
        if not self.api_key:
            logger.warning(
                "INTERNAL_API_KEY not set. Backend API calls will fail."
            )
        
        # HTTP client with timeout
        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=10.0,
            headers={
                "X-API-Key": self.api_key or "",
                "Content-Type": "application/json",
            }
        )
    
    async def get_user_details(self, user_id: str) -> Dict[str, Any]:
        """
        Get user details from backend API.
        
        Args:
            user_id: User identifier
            
        Returns:
            User details dictionary with email, name, roles, permissions, etc.
            
        Raises:
            ValueError: If API call fails or user not found
        """
        if not self.api_key:
            raise ValueError("INTERNAL_API_KEY not configured")
        
        try:
            response = await self.client.get(
                f"/api/internal/users/{user_id}"
            )
            response.raise_for_status()
            data = response.json()
            return data.get("user", {})
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                raise ValueError(f"User {user_id} not found")
            elif e.response.status_code == 401:
                raise ValueError("Invalid API key for backend API")
            else:
                logger.error(f"Backend API error: {e}")
                raise ValueError(f"Failed to fetch user details: {str(e)}")
        except httpx.HTTPError as e:
            logger.error(f"Backend API request failed: {e}")
            raise ValueError(f"Failed to connect to backend API: {str(e)}")
    
    async def get_beneficiaries(self, user_id: str) -> List[Dict[str, Any]]:
        """Get user beneficiaries from backend API."""
        if not self.api_key:
            raise ValueError("INTERNAL_API_KEY not configured")
            
        try:
            response = await self.client.get(
                f"/api/internal/users/{user_id}/beneficiaries"
            )
            response.raise_for_status()
            return response.json().get("beneficiaries", [])
        except httpx.HTTPError as e:
            logger.error(f"Backend API request failed: {e}")
            return [] # Return empty list on error to fail gracefully
    
    async def get_banking_accounts(self, user_id: str) -> List[Dict[str, Any]]:
        """
        Get banking accounts for a user (server-to-server).
        
        Args:
            user_id: User identifier
            
        Returns:
            List of account dictionaries
        """
        if not self.api_key:
            raise ValueError("INTERNAL_API_KEY not configured")
        
        try:
            response = await self.client.get(
                f"/api/internal/banking/accounts/{user_id}"
            )
            response.raise_for_status()
            data = response.json()
            return data.get("data", [])
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                raise ValueError(f"User {user_id} not found")
            elif e.response.status_code == 401:
                raise ValueError("Invalid API key for backend API")
            else:
                logger.error(f"Backend API error: {e}")
                raise ValueError(f"Failed to fetch accounts: {str(e)}")
        except httpx.HTTPError as e:
            logger.error(f"Backend API request failed: {e}")
            raise ValueError(f"Failed to connect to backend API: {str(e)}")
    
    async def get_banking_transactions(
        self,
        user_id: str,
        account_type: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        limit: int = 10,
        offset: int = 0
    ) -> Dict[str, Any]:
        """
        Get banking transactions for a user (server-to-server).
        
        Args:
            user_id: User identifier
            account_type: Optional account type filter
            start_date: Optional start date filter
            end_date: Optional end date filter
            limit: Maximum number of transactions
            offset: Pagination offset
            
        Returns:
            Dictionary with data and meta keys
        """
        if not self.api_key:
            raise ValueError("INTERNAL_API_KEY not configured")
        
        try:
            params = []
            if account_type:
                params.append(f"accountType={account_type}")
            if start_date:
                params.append(f"startDate={start_date}")
            if end_date:
                params.append(f"endDate={end_date}")
            if limit:
                params.append(f"limit={limit}")
            if offset:
                params.append(f"offset={offset}")
            
            url = f"/api/internal/banking/transactions/{user_id}"
            if params:
                url += "?" + "&".join(params)
            
            response = await self.client.get(url)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                raise ValueError(f"User {user_id} not found")
            elif e.response.status_code == 401:
                raise ValueError("Invalid API key for backend API")
            else:
                logger.error(f"Backend API error: {e}")
                raise ValueError(f"Failed to fetch transactions: {str(e)}")
        except httpx.HTTPError as e:
            logger.error(f"Backend API request failed: {e}")
            raise ValueError(f"Failed to connect to backend API: {str(e)}")
    
    async def close(self):
        """Close HTTP client."""
        await self.client.aclose()


# Singleton instance
_backend_client: Optional[BackendAPIClient] = None


def get_backend_client() -> BackendAPIClient:
    """
    Get singleton backend API client instance.
    
    Returns:
        BackendAPIClient instance
    """
    global _backend_client
    if _backend_client is None:
        _backend_client = BackendAPIClient()
    return _backend_client

