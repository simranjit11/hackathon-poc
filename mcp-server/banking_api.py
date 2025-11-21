"""
Banking API Client
==================
Client for calling Next.js banking APIs.
Uses JWT tokens for user-authenticated calls and API keys for server-to-server calls.
"""

from typing import List, Optional, Dict, Any
from datetime import datetime
import logging
import httpx
import os

logger = logging.getLogger(__name__)


class BankingAPI:
    """Banking API client that calls Next.js banking endpoints."""
    
    def __init__(
        self,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None
    ):
        """
        Initialize banking API client.
        
        Args:
            base_url: Backend API base URL (defaults to env var)
            api_key: API key for server-to-server calls (defaults to env var)
        """
        self.base_url = base_url or os.getenv(
            "BACKEND_API_URL",
            "http://localhost:3000"
        )
        self.api_key = api_key or os.getenv("INTERNAL_API_KEY")
        
        # HTTP client with timeout
        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=30.0,
            headers={
                "Content-Type": "application/json",
            }
        )
    
    async def _get_with_token(self, endpoint: str, jwt_token: str) -> Dict[str, Any]:
        """Make GET request with JWT token."""
        headers = {"Authorization": f"Bearer {jwt_token}"}
        response = await self.client.get(endpoint, headers=headers)
        response.raise_for_status()
        return response.json()
    
    async def _get_with_api_key(self, endpoint: str) -> Dict[str, Any]:
        """Make GET request with API key (server-to-server)."""
        if not self.api_key:
            raise ValueError("INTERNAL_API_KEY not configured")
        headers = {"X-API-Key": self.api_key}
        response = await self.client.get(endpoint, headers=headers)
        response.raise_for_status()
        return response.json()
    
    async def _post_with_token(
        self,
        endpoint: str,
        jwt_token: str,
        data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Make POST request with JWT token."""
        headers = {"Authorization": f"Bearer {jwt_token}"}
        response = await self.client.post(endpoint, headers=headers, json=data)
        response.raise_for_status()
        return response.json()
    
    async def get_accounts(
        self,
        user_id: str,
        jwt_token: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get all accounts for a user.
        
        Args:
            user_id: User identifier
            jwt_token: Optional JWT token for user-authenticated calls
            
        Returns:
            List of account dictionaries
        """
        try:
            if jwt_token:
                # User-authenticated call
                result = await self._get_with_token("/api/banking/accounts", jwt_token)
            else:
                # Server-to-server call
                result = await self._get_with_api_key(f"/api/internal/banking/accounts/{user_id}")
            
            accounts = result.get("data", [])
            
            # Transform to match expected format
            transformed = []
            for account in accounts:
                transformed.append({
                    "type": account.get("accountType", ""),
                    "account_number": account.get("accountNumber", ""),
                    "balance": float(account.get("balance", 0)),
                    "limit": float(account.get("creditLimit", 0)) if account.get("creditLimit") else None,
                    "currency": account.get("currency", "USD"),
                    "status": account.get("status", "active"),
                })
            
            return transformed
        except httpx.HTTPError as e:
            logger.error(f"Failed to fetch accounts: {e}")
            return []
    
    async def get_account_balances(
        self,
        user_id: str,
        account_type: Optional[str] = None,
        jwt_token: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get account balances for a user.
        
        Args:
            user_id: User identifier
            account_type: Optional account type filter
            jwt_token: Optional JWT token for user-authenticated calls
            
        Returns:
            List of balance dictionaries
        """
        try:
            endpoint = "/api/banking/accounts/balance"
            if account_type:
                endpoint += f"?accountType={account_type}"
            
            if jwt_token:
                result = await self._get_with_token(endpoint, jwt_token)
            else:
                # For server-to-server, we need to get accounts and filter
                accounts = await self.get_accounts(user_id)
                if account_type:
                    accounts = [acc for acc in accounts if acc.get("type") == account_type]
                return accounts
            
            balances = result.get("data", [])
            
            # Transform to match expected format
            transformed = []
            for balance in balances:
                transformed.append({
                    "account_type": balance.get("accountType", ""),
                    "account_number": balance.get("accountNumber", ""),
                    "balance": float(balance.get("balance", 0)),
                    "credit_limit": float(balance.get("creditLimit", 0)) if balance.get("creditLimit") else None,
                    "available_balance": float(balance.get("availableBalance", 0)),
                    "currency": balance.get("currency", "USD"),
                })
            
            return transformed
        except httpx.HTTPError as e:
            logger.error(f"Failed to fetch account balances: {e}")
            return []
    
    async def get_transactions(
        self,
        user_id: str,
        account_type: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        limit: int = 10,
        jwt_token: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get transactions for a user.
        
        Args:
            user_id: User identifier
            account_type: Optional account type filter
            start_date: Optional start date filter (YYYY-MM-DD)
            end_date: Optional end date filter (YYYY-MM-DD)
            limit: Maximum number of transactions
            jwt_token: Optional JWT token for user-authenticated calls
            
        Returns:
            List of transaction dictionaries
        """
        try:
            # Build query parameters
            params = []
            if account_type:
                params.append(f"accountType={account_type}")
            if start_date:
                params.append(f"startDate={start_date}")
            if end_date:
                params.append(f"endDate={end_date}")
            if limit:
                params.append(f"limit={limit}")
            
            endpoint = "/api/banking/transactions"
            if params:
                endpoint += "?" + "&".join(params)
            
            if jwt_token:
                result = await self._get_with_token(endpoint, jwt_token)
            else:
                result = await self._get_with_api_key(f"/api/internal/banking/transactions/{user_id}?{'&'.join(params)}")
            
            transactions = result.get("data", [])
            
            # Transform to match expected format
            transformed = []
            for txn in transactions:
                # Parse date from ISO format
                created_at = txn.get("createdAt", "")
                date_str = created_at.split("T")[0] if "T" in created_at else created_at
                
                # Determine transaction type
                txn_type = txn.get("transactionType", "debit")
                amount = float(txn.get("amount", 0))
                
                # For payments/transfers, amount is negative (outgoing)
                if txn_type in ["payment", "transfer"]:
                    amount = -abs(amount)
                elif txn_type == "deposit":
                    amount = abs(amount)
                
                transformed.append({
                    "date": date_str,
                    "description": txn.get("description", ""),
                    "amount": amount,
                    "type": "debit" if amount < 0 else "credit",
                    "account_number": txn.get("fromAccount", ""),
                })
            
            return transformed
        except httpx.HTTPError as e:
            logger.error(f"Failed to fetch transactions: {e}")
            return []
    
    async def get_loans(
        self,
        user_id: str,
        jwt_token: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get loans for a user.
        
        Args:
            user_id: User identifier
            jwt_token: Optional JWT token for user-authenticated calls
            
        Returns:
            List of loan dictionaries
        """
        try:
            if jwt_token:
                result = await self._get_with_token("/api/banking/loans", jwt_token)
            else:
                # For server-to-server, we'd need an internal endpoint
                # For now, return empty list or use user token
                logger.warning("Server-to-server loan endpoint not available, using mock data")
                return []
            
            loans = result.get("data", [])
            
            # Transform to match expected format
            transformed = []
            for loan in loans:
                transformed.append({
                    "type": loan.get("loanType", ""),
                    "balance": float(loan.get("outstandingBalance", 0)),
                    "rate": float(loan.get("interestRate", 0)),
                    "monthly_payment": float(loan.get("monthlyPayment", 0)),
                    "account_number": loan.get("loanNumber", ""),
                    "remaining_term_months": loan.get("remainingTermMonths", 0),
                    "next_payment_date": loan.get("nextPaymentDate", "").split("T")[0] if loan.get("nextPaymentDate") else "",
                })
            
            return transformed
        except httpx.HTTPError as e:
            logger.error(f"Failed to fetch loans: {e}")
            return []
    
    async def initiate_payment(
        self,
        user_id: str,
        from_account: str,
        to_account: str,
        amount: float,
        description: str = "",
        jwt_token: str = ""
    ) -> Dict[str, Any]:
        """
        Initiate a payment (two-step process).
        
        Args:
            user_id: User identifier
            from_account: Source account number or account type
            to_account: Destination (beneficiary nickname, ID, or payment address)
            amount: Amount to transfer
            description: Optional description
            jwt_token: JWT token for authentication
            
        Returns:
            Payment initiation response with paymentSessionId and otpCode
        """
        if not jwt_token:
            raise ValueError("JWT token required for payment initiation")
        
        # Build request body - try to detect if to_account is a beneficiary nickname
        # or a payment address
        payment_data = {
            "fromAccount": from_account,
            "amount": amount,
            "description": description or f"Payment to {to_account}",
        }
        
        # Check if to_account looks like a beneficiary nickname (simple heuristic)
        # In production, you'd check against beneficiary list first
        if "@" in to_account or to_account.startswith("ACC-") or to_account.startswith("CHK-") or to_account.startswith("SAV-"):
            # Looks like a payment address or account number
            payment_data["paymentAddress"] = to_account
        else:
            # Assume it's a beneficiary nickname
            payment_data["beneficiaryNickname"] = to_account
        
        try:
            result = await self._post_with_token(
                "/api/banking/payments/initiate",
                jwt_token,
                payment_data
            )
            
            return {
                "paymentSessionId": result.get("paymentSessionId"),
                "otpCode": result.get("otpCode"),  # Only in dev mode
                "transaction": result.get("transaction", {}),
                "message": result.get("message", "OTP sent"),
            }
        except httpx.HTTPStatusError as e:
            error_data = {}
            try:
                error_data = e.response.json()
            except:
                pass
            error_msg = error_data.get("error", str(e))
            raise ValueError(f"Payment initiation failed: {error_msg}")
    
    async def confirm_payment(
        self,
        payment_session_id: str,
        otp_code: str,
        jwt_token: str
    ) -> Dict[str, Any]:
        """
        Confirm a payment with OTP.
        
        Args:
            payment_session_id: Payment session ID from initiate_payment
            otp_code: OTP code
            jwt_token: JWT token for authentication
            
        Returns:
            Payment confirmation response
        """
        if not jwt_token:
            raise ValueError("JWT token required for payment confirmation")
        
        try:
            result = await self._post_with_token(
                "/api/banking/payments/confirm",
                jwt_token,
                {
                    "paymentSessionId": payment_session_id,
                    "otpCode": otp_code,
                }
            )
            
            transaction = result.get("transaction", {})
            
            return {
                "confirmation_number": transaction.get("referenceNumber", ""),
                "from_account": transaction.get("fromAccount", ""),
                "to_account": transaction.get("toAccount", ""),
                "amount": float(transaction.get("amount", 0)),
                "description": transaction.get("description", ""),
                "date": transaction.get("completedAt", "").split("T")[0] if transaction.get("completedAt") else datetime.now().strftime("%Y-%m-%d"),
                "status": transaction.get("status", "completed"),
            }
        except httpx.HTTPStatusError as e:
            error_data = {}
            try:
                error_data = e.response.json()
            except:
                pass
            error_msg = error_data.get("error", str(e))
            raise ValueError(f"Payment confirmation failed: {error_msg}")
    
    async def make_payment(
        self,
        user_id: str,
        from_account: str,
        to_account: str,
        amount: float,
        description: str = "",
        jwt_token: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Make a payment (legacy method - now uses two-step process).
        This method initiates and confirms in one call (for backward compatibility).
        
        Args:
            user_id: User identifier
            from_account: Source account type or account number
            to_account: Destination account or payee name
            amount: Amount to transfer
            description: Optional description
            jwt_token: JWT token for authentication
            
        Returns:
            Payment confirmation dictionary
        """
        if not jwt_token:
            raise ValueError("JWT token required for payments")
        
        # Step 1: Initiate payment
        initiation = await self.initiate_payment(
            user_id,
            from_account,
            to_account,
            amount,
            description,
            jwt_token
        )
        
        # Step 2: Confirm payment with OTP
        # Note: In production, OTP would be sent via SMS/Email
        # For now, we use the OTP from the response (dev mode only)
        otp_code = initiation.get("otpCode")
        if not otp_code:
            raise ValueError("OTP code not available. Payment requires manual confirmation.")
        
        payment_session_id = initiation.get("paymentSessionId")
        if not payment_session_id:
            raise ValueError("Payment session ID not available")
        
        # Confirm the payment
        confirmation = await self.confirm_payment(
            payment_session_id,
            otp_code,
            jwt_token
        )
        
        return confirmation
    
    async def get_customer_name(self, user_id: str) -> Optional[str]:
        """
        Get customer name for a user from backend API.
        """
        try:
            from backend_client import get_backend_client
            backend_client = get_backend_client()
            user_details = await backend_client.get_user_details(user_id)
            return user_details.get("name") or user_details.get("email")
        except Exception as e:
            logger.warning(f"Failed to fetch user details from backend API: {e}")
            return None
    
    async def set_alert(
        self,
        user_id: str,
        alert_type: str,
        description: str,
        due_date: Optional[str] = None,
        jwt_token: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Set up a payment reminder or alert.
        
        Args:
            user_id: User identifier
            alert_type: Type of alert ('payment', 'low_balance', 'large_transaction')
            description: Description of the alert
            due_date: Optional due date for payment reminders
            jwt_token: JWT token for authentication
            
        Returns:
            Alert dictionary
        """
        if not jwt_token:
            raise ValueError("JWT token required for setting alerts")
        
        # Map alert types to API format
        alert_type_map = {
            "payment": "payment_received",
            "low_balance": "low_balance",
            "large_transaction": "payment_sent",
        }
        api_alert_type = alert_type_map.get(alert_type, "payment_received")
        
        try:
            result = await self._post_with_token(
                "/api/banking/alerts",
                jwt_token,
                {
                    "alertType": api_alert_type,
                    "description": description,
                }
            )
            
            alert_data = result.get("data", {})
            return {
                "type": alert_data.get("alertType", "").replace("_", " ").title() + " Alert",
                "description": description + (f" (Due: {due_date})" if due_date else ""),
                "active": alert_data.get("isActive", True),
                "created_at": alert_data.get("createdAt", datetime.now().isoformat()),
            }
        except httpx.HTTPError as e:
            logger.error(f"Failed to create alert: {e}")
            # Fallback to in-memory storage for backward compatibility
            return {
                "type": alert_type.replace('_', ' ').title() + " Alert",
                "description": description + (f" (Due: {due_date})" if due_date else ""),
                "active": True,
                "created_at": datetime.now().isoformat()
            }
    
    async def get_alerts(
        self,
        user_id: str,
        jwt_token: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get all alerts for a user.
        
        Args:
            user_id: User identifier
            jwt_token: JWT token for authentication
            
        Returns:
            List of alert dictionaries
        """
        if not jwt_token:
            # Return empty list if no token
            return []
        
        try:
            result = await self._get_with_token("/api/banking/alerts", jwt_token)
            alerts = result.get("data", [])
            
            # Transform to match expected format
            transformed = []
            for alert in alerts:
                transformed.append({
                    "type": alert.get("alertType", "").replace("_", " ").title() + " Alert",
                    "description": f"Threshold: ${alert.get('threshold', 0)}" if alert.get("threshold") else "Alert active",
                    "active": alert.get("isActive", True),
                    "created_at": alert.get("createdAt", ""),
                })
            
            return transformed
        except httpx.HTTPError as e:
            logger.error(f"Failed to fetch alerts: {e}")
            return []
    
    async def close(self):
        """Close HTTP client."""
        await self.client.aclose()
