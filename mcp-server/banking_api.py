"""
Banking API Client
==================
Client for calling Next.js banking APIs.
Uses API key authentication for server-to-server calls.
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
    
    async def _get_with_api_key(self, endpoint: str) -> Dict[str, Any]:
        """Make GET request with API key (server-to-server)."""
        if not self.api_key:
            raise ValueError("INTERNAL_API_KEY not configured")
        headers = {"X-API-Key": self.api_key}
        response = await self.client.get(endpoint, headers=headers)
        response.raise_for_status()
        return response.json()
    
    async def _post_with_api_key(
        self,
        endpoint: str,
        data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Make POST request with API key (server-to-server)."""
        if not self.api_key:
            raise ValueError("INTERNAL_API_KEY not configured")
        headers = {"X-API-Key": self.api_key}
        response = await self.client.post(endpoint, headers=headers, json=data)
        if not response.is_success:
            # Log error response body for debugging
            try:
                error_body = response.json()
                logger.error(f"API error response: {error_body}")
            except Exception:
                error_text = response.text
                logger.error(f"API error response (non-JSON): {error_text}")
        response.raise_for_status()
        return response.json()
    
    async def _put_with_api_key(
        self,
        endpoint: str,
        data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Make PUT request with API key (server-to-server)."""
        if not self.api_key:
            raise ValueError("INTERNAL_API_KEY not configured")
        headers = {"X-API-Key": self.api_key}
        response = await self.client.put(endpoint, headers=headers, json=data)
        if not response.is_success:
            # Log error response body for debugging
            try:
                error_body = response.json()
                logger.error(f"API error response: {error_body}")
            except Exception:
                error_text = response.text
                logger.error(f"API error response (non-JSON): {error_text}")
        response.raise_for_status()
        return response.json()
    
    async def _delete_with_api_key(
        self,
        endpoint: str
    ) -> bool:
        """Make DELETE request with API key (server-to-server)."""
        if not self.api_key:
            raise ValueError("INTERNAL_API_KEY not configured")
        headers = {"X-API-Key": self.api_key}
        response = await self.client.delete(endpoint, headers=headers)
        if not response.is_success:
            # Log error response body for debugging
            try:
                error_body = response.json()
                logger.error(f"API error response: {error_body}")
            except Exception:
                error_text = response.text
                logger.error(f"API error response (non-JSON): {error_text}")
        response.raise_for_status()
        return True
    
    async def get_accounts(
        self,
        user_id: str
    ) -> List[Dict[str, Any]]:
        """
        Get all accounts for a user.
        
        Args:
            user_id: User identifier
            
        Returns:
            List of account dictionaries
        """
        try:
            result = await self._get_with_api_key(f"/api/internal/banking/accounts/{user_id}")
            
            accounts = result.get("data", [])
            
            # Transform to match expected format
            transformed = []
            for account in accounts:
                transformed.append({
                    "id": account.get("id", ""),  # Include account ID
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
        account_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get account balances for a user via internal API.
        
        Args:
            user_id: User identifier
            account_type: Optional account type filter
            
        Returns:
            List of balance dictionaries
        """
        try:
            accounts = await self.get_accounts(user_id)
            if account_type:
                accounts = [acc for acc in accounts if acc.get("type") == account_type]
            return accounts
            
        except httpx.HTTPError as e:
            logger.error(f"Failed to fetch account balances: {e}")
            return []
    
    async def get_transactions(
        self,
        user_id: str,
        account_type: Optional[str] = None,
        account_id: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        limit: int = 10,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        Get transactions for a user with pagination support.
        
        Args:
            user_id: User identifier
            account_type: Optional account type filter (checking, savings, credit_card)
            account_id: Optional account ID filter (UUID). If not provided, defaults to savings account
            start_date: Optional start date filter (YYYY-MM-DD)
            end_date: Optional end date filter (YYYY-MM-DD)
            limit: Maximum number of transactions (default: 10, max: 100)
            offset: Number of transactions to skip for pagination (default: 0)
            
        Returns:
            List of transaction dictionaries
        """
        try:
            # Build query parameters
            params = []
            if account_type:
                params.append(f"accountType={account_type}")
            if account_id:
                params.append(f"accountId={account_id}")
            if start_date:
                params.append(f"startDate={start_date}")
            if end_date:
                params.append(f"endDate={end_date}")
            if limit:
                params.append(f"limit={limit}")
            if offset:
                params.append(f"offset={offset}")
            
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
        user_id: str
    ) -> List[Dict[str, Any]]:
        """
        Get loans for a user.
        
        Args:
            user_id: User identifier
            
        Returns:
            List of loan dictionaries
        """
        try:
            result = await self._get_with_api_key(f"/api/internal/banking/loans/{user_id}")
            
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
        description: str = ""
    ) -> Dict[str, Any]:
        """
        Initiate a payment (two-step process) via internal API.
        
        Args:
            user_id: User identifier
            from_account: Source account number or account type
            to_account: Destination (beneficiary nickname, ID, or payment address)
            amount: Amount to transfer
            description: Optional description
            
        Returns:
            Payment initiation response with paymentSessionId and otpCode
        """
        # Build request body for internal API
        payment_data = {
            "userId": user_id,
            "fromAccount": from_account,
            "amount": amount,
            "description": description or f"Payment to {to_account}",
        }
        
        # Check if to_account looks like a beneficiary nickname (simple heuristic)
        # or a payment address
        if "@" in to_account or to_account.startswith("ACC-") or to_account.startswith("CHK-") or to_account.startswith("SAV-"):
            # Looks like a payment address or account number
            payment_data["paymentAddress"] = to_account
        else:
            # Assume it's a beneficiary nickname
            payment_data["beneficiaryNickname"] = to_account
        
        try:
            # Call internal API with API key authentication
            result = await self._post_with_api_key(
                "/api/internal/banking/payments/initiate",
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
        user_id: str,
        payment_session_id: str,
        otp_code: str
    ) -> Dict[str, Any]:
        """
        Confirm a payment with OTP via internal API.
        
        Args:
            user_id: User identifier
            payment_session_id: Payment session ID from initiate_payment
            otp_code: OTP code
            
        Returns:
            Payment confirmation response
        """
        try:
            # Call internal API with API key authentication
            result = await self._post_with_api_key(
                "/api/internal/banking/payments/confirm",
                {
                    "userId": user_id,
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
        description: str = ""
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
            
        Returns:
            Payment confirmation dictionary
        """
        # Step 1: Initiate payment
        initiation = await self.initiate_payment(
            user_id,
            from_account,
            to_account,
            amount,
            description
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
            user_id,
            payment_session_id,
            otp_code
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
    
    async def create_reminder(
        self,
        user_id: str,
        scheduled_date: str,
        amount: float,
        recipient: str,
        description: str = "",
        beneficiary_id: Optional[str] = None,
        beneficiary_nickname: Optional[str] = None,
        account_id: Optional[str] = None,
        reminder_notification_settings: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Create a payment reminder.
        
        Args:
            user_id: User identifier
            scheduled_date: ISO 8601 date string for scheduled payment
            amount: Payment amount
            recipient: Recipient name or payment address
            description: Description of the reminder
            beneficiary_id: Optional beneficiary ID
            beneficiary_nickname: Optional beneficiary nickname
            account_id: Account ID for payment (required)
            reminder_notification_settings: Optional notification settings
            
        Returns:
            Reminder dictionary
        """
        if not account_id:
            raise ValueError("account_id is required")
        
        try:
            payload = {
                "userId": user_id,  # Include user_id for internal API
                "scheduledDate": scheduled_date,
                "amount": amount,
                "recipient": recipient,
                "accountId": account_id,
            }
            
            # Only include optional fields if they have non-empty values
            # Don't send empty strings - they might cause validation issues
            if description and description.strip():
                payload["description"] = description.strip()
            
            # Only include beneficiary fields if they have values
            # Note: beneficiary_id and beneficiary_nickname are mutually exclusive
            if beneficiary_id and beneficiary_id.strip():
                payload["beneficiaryId"] = beneficiary_id.strip()
            elif beneficiary_nickname and beneficiary_nickname.strip():
                payload["beneficiaryNickname"] = beneficiary_nickname.strip()
            
            if reminder_notification_settings:
                payload["reminderNotificationSettings"] = reminder_notification_settings
            
            logger.info(f"Creating reminder with payload keys: {list(payload.keys())}")
            logger.debug(f"Creating reminder with payload: {payload}")
            
            result = await self._post_with_api_key(
                "/api/internal/banking/reminders",
                payload
            )
            
            reminder_data = result.get("data", {})
            return {
                "id": reminder_data.get("id", ""),
                "scheduledDate": reminder_data.get("scheduledDate", scheduled_date),
                "amount": reminder_data.get("amount", amount),
                "recipient": reminder_data.get("recipient", recipient),
                "description": reminder_data.get("description", description),
                "isCompleted": reminder_data.get("isCompleted", False),
                "created_at": reminder_data.get("createdAt", datetime.now().isoformat()),
            }
        except httpx.HTTPStatusError as e:
            # Extract error message from response
            error_msg = f"Failed to create reminder: {e.response.status_code}"
            try:
                error_body = e.response.json()
                if "error" in error_body:
                    error_msg = f"Failed to create reminder: {error_body['error']}"
                logger.error(f"API error: {error_msg}, response: {error_body}")
            except Exception:
                error_text = e.response.text
                logger.error(f"API error: {error_msg}, response text: {error_text[:200]}")
            raise ValueError(error_msg)
        except httpx.HTTPError as e:
            logger.error(f"Failed to create reminder: {e}")
            raise ValueError(f"Failed to create reminder: {e}")
    
    async def get_reminders(
        self,
        user_id: str,
        is_completed: Optional[bool] = None,
        scheduled_date_from: Optional[str] = None,
        scheduled_date_to: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get all payment reminders for a user.
        
        Args:
            user_id: User identifier
            is_completed: Optional filter by completion status
            scheduled_date_from: Optional filter by scheduled date from (ISO 8601)
            scheduled_date_to: Optional filter by scheduled date to (ISO 8601)
            
        Returns:
            List of reminder dictionaries
        """
        try:
            params = [f"userId={user_id}"]
            if is_completed is not None:
                params.append(f"isCompleted={str(is_completed).lower()}")
            if scheduled_date_from:
                params.append(f"scheduledDateFrom={scheduled_date_from}")
            if scheduled_date_to:
                params.append(f"scheduledDateTo={scheduled_date_to}")
            
            query_string = "&".join(params)
            url = f"/api/internal/banking/reminders?{query_string}"
            
            result = await self._get_with_api_key(url)
            reminders = result.get("data", [])
            
            # Transform to match expected format
            transformed = []
            for reminder in reminders:
                transformed.append({
                    "id": reminder.get("id", ""),
                    "scheduledDate": reminder.get("scheduledDate", ""),
                    "amount": reminder.get("amount", 0),
                    "recipient": reminder.get("recipient", ""),
                    "description": reminder.get("description", ""),
                    "isCompleted": reminder.get("isCompleted", False),
                    "created_at": reminder.get("createdAt", ""),
                })
            
            return transformed
        except httpx.HTTPError as e:
            logger.error(f"Failed to fetch reminders: {e}")
            return []
    
    async def update_reminder(
        self,
        user_id: str,
        reminder_id: str,
        scheduled_date: Optional[str] = None,
        amount: Optional[float] = None,
        recipient: Optional[str] = None,
        description: Optional[str] = None,
        beneficiary_id: Optional[str] = None,
        beneficiary_nickname: Optional[str] = None,
        account_id: Optional[str] = None,
        is_completed: Optional[bool] = None,
        reminder_notification_settings: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Update a payment reminder.
        
        Args:
            user_id: User identifier
            reminder_id: Reminder ID to update
            scheduled_date: Optional ISO 8601 date string for scheduled payment
            amount: Optional payment amount
            recipient: Optional recipient name or payment address
            description: Optional description of the reminder
            beneficiary_id: Optional beneficiary ID
            beneficiary_nickname: Optional beneficiary nickname
            account_id: Optional account ID for payment
            is_completed: Optional completion status
            reminder_notification_settings: Optional notification settings
            
        Returns:
            Updated reminder dictionary
        """
        try:
            payload: Dict[str, Any] = {
                "userId": user_id
            }
            
            if scheduled_date is not None:
                payload["scheduledDate"] = scheduled_date
            if amount is not None:
                payload["amount"] = amount
            if recipient is not None:
                payload["recipient"] = recipient
            if description is not None:
                payload["description"] = description
            if beneficiary_id is not None:
                payload["beneficiaryId"] = beneficiary_id
            if beneficiary_nickname is not None:
                payload["beneficiaryNickname"] = beneficiary_nickname
            if account_id is not None:
                payload["accountId"] = account_id
            if is_completed is not None:
                payload["isCompleted"] = is_completed
            if reminder_notification_settings is not None:
                payload["reminderNotificationSettings"] = reminder_notification_settings
            
            result = await self._put_with_api_key(
                f"/api/internal/banking/reminders/{reminder_id}",
                payload
            )
            
            reminder_data = result.get("data", {})
            return {
                "id": reminder_data.get("id", reminder_id),
                "scheduledDate": reminder_data.get("scheduledDate", scheduled_date),
                "amount": reminder_data.get("amount", amount),
                "recipient": reminder_data.get("recipient", recipient),
                "description": reminder_data.get("description", description),
                "isCompleted": reminder_data.get("isCompleted", is_completed),
                "updated_at": reminder_data.get("updatedAt", datetime.now().isoformat()),
            }
        except httpx.HTTPError as e:
            logger.error(f"Failed to update reminder: {e}")
            raise ValueError(f"Failed to update reminder: {e}")
    
    async def delete_reminder(
        self,
        user_id: str,
        reminder_id: str
    ) -> bool:
        """
        Delete a payment reminder.
        
        Args:
            user_id: User identifier
            reminder_id: Reminder ID to delete
            
        Returns:
            True if successful
        """
        try:
            await self._delete_with_api_key(
                f"/api/internal/banking/reminders/{reminder_id}?userId={user_id}"
            )
            return True
        except httpx.HTTPError as e:
            logger.error(f"Failed to delete reminder: {e}")
            raise ValueError(f"Failed to delete reminder: {e}")
    
    async def close(self):
        """Close HTTP client."""
        await self.client.aclose()
