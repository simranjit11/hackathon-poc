"""
Banking API Client
==================
Mock banking API that returns account data.
In production, this would call an external banking service.
"""

from typing import List, Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)


class BankingAPI:
    """Mock banking API client."""
    
    # Mock customer accounts database (matching agent.py structure)
    _accounts = {
        "12345": {
            "customer_name": "John Doe",
            "checking": {
                "balance": 2547.83,
                "account_number": "CHK-12345-001",
                "type": "checking"
            },
            "savings": {
                "balance": 15430.22,
                "account_number": "SAV-12345-002",
                "type": "savings"
            },
            "credit_card": {
                "balance": 1250.45,
                "limit": 5000.00,
                "account_number": "CC-12345-003",
                "type": "credit_card"
            }
        },
        "67890": {
            "customer_name": "Jane Smith",
            "checking": {
                "balance": 3821.67,
                "account_number": "CHK-67890-001",
                "type": "checking"
            },
            "savings": {
                "balance": 25678.90,
                "account_number": "SAV-67890-002",
                "type": "savings"
            },
            "credit_card": {
                "balance": 2100.30,
                "limit": 8000.00,
                "account_number": "CC-67890-003",
                "type": "credit_card"
            }
        }
    }
    
    # Mock transaction history
    _transactions = {
        "12345": [
            {
                "date": "2025-11-05",
                "description": "Grocery Store",
                "amount": -87.32,
                "type": "debit",
                "account_number": "CHK-12345-001"
            },
            {
                "date": "2025-11-04",
                "description": "Salary Deposit",
                "amount": 3200.00,
                "type": "credit",
                "account_number": "CHK-12345-001"
            },
            {
                "date": "2025-11-03",
                "description": "Gas Station",
                "amount": -45.67,
                "type": "debit",
                "account_number": "CHK-12345-001"
            },
            {
                "date": "2025-11-02",
                "description": "Online Transfer",
                "amount": -500.00,
                "type": "transfer",
                "account_number": "CHK-12345-001"
            },
            {
                "date": "2025-11-01",
                "description": "Coffee Shop",
                "amount": -12.95,
                "type": "debit",
                "account_number": "CHK-12345-001"
            }
        ],
        "67890": [
            {
                "date": "2025-11-05",
                "description": "Rent Payment",
                "amount": -1800.00,
                "type": "debit",
                "account_number": "CHK-67890-001"
            },
            {
                "date": "2025-11-04",
                "description": "Freelance Payment",
                "amount": 1250.00,
                "type": "credit",
                "account_number": "CHK-67890-001"
            },
            {
                "date": "2025-11-03",
                "description": "Utility Bill",
                "amount": -125.40,
                "type": "debit",
                "account_number": "CHK-67890-001"
            },
            {
                "date": "2025-11-02",
                "description": "Investment Deposit",
                "amount": -1000.00,
                "type": "transfer",
                "account_number": "CHK-67890-001"
            },
            {
                "date": "2025-11-01",
                "description": "Restaurant",
                "amount": -85.60,
                "type": "debit",
                "account_number": "CHK-67890-001"
            }
        ]
    }
    
    # Mock loan information
    _loans = {
        "12345": [
            {
                "type": "Mortgage",
                "balance": 285000.00,
                "rate": 3.75,
                "monthly_payment": 1820.50,
                "account_number": "LOAN-12345-001",
                "remaining_term_months": 312,
                "next_payment_date": "2025-12-01"
            },
            {
                "type": "Auto Loan",
                "balance": 18500.00,
                "rate": 4.25,
                "monthly_payment": 435.20,
                "account_number": "LOAN-12345-002",
                "remaining_term_months": 48,
                "next_payment_date": "2025-12-15"
            }
        ],
        "67890": [
            {
                "type": "Personal Loan",
                "balance": 8500.00,
                "rate": 6.50,
                "monthly_payment": 275.80,
                "account_number": "LOAN-67890-001",
                "remaining_term_months": 36,
                "next_payment_date": "2025-12-10"
            }
        ]
    }
    
    async def get_accounts(self, user_id: str) -> List[Dict[str, Any]]:
        """
        Get all accounts for a user.
        
        Args:
            user_id: User identifier
            
        Returns:
            List of account dictionaries
        """
        if user_id not in self._accounts:
            logger.warning(f"User {user_id} not found in accounts")
            return []
        
        customer = self._accounts[user_id]
        accounts = []
        
        for account_type in ["checking", "savings", "credit_card"]:
            if account_type in customer:
                account = customer[account_type].copy()
                accounts.append(account)
        
        return accounts
    
    async def get_transactions(
        self,
        user_id: str,
        account_type: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Get transactions for a user.
        
        Args:
            user_id: User identifier
            account_type: Optional account type filter
            start_date: Optional start date filter (YYYY-MM-DD)
            end_date: Optional end date filter (YYYY-MM-DD)
            limit: Maximum number of transactions
            
        Returns:
            List of transaction dictionaries
        """
        if user_id not in self._transactions:
            logger.warning(f"User {user_id} not found in transactions")
            return []
        
        transactions = self._transactions[user_id].copy()
        
        # Filter by account_type if specified
        if account_type:
            transactions = [
                txn for txn in transactions
                if account_type.lower() in txn.get("account_number", "").lower()
            ]
        
        # Filter by date range if specified
        if start_date:
            transactions = [
                txn for txn in transactions
                if txn.get("date", "") >= start_date
            ]
        
        if end_date:
            transactions = [
                txn for txn in transactions
                if txn.get("date", "") <= end_date
            ]
        
        # Limit results
        return transactions[:limit]
    
    async def get_loans(self, user_id: str) -> List[Dict[str, Any]]:
        """
        Get loans for a user.
        
        Args:
            user_id: User identifier
            
        Returns:
            List of loan dictionaries
        """
        if user_id not in self._loans:
            logger.warning(f"User {user_id} not found in loans")
            return []
        
        return self._loans[user_id].copy()

