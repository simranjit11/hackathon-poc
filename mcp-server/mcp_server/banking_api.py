"""
Banking API Client
==================
Fetches banking data from PostgreSQL database.
"""

from typing import List, Optional, Dict, Any
import logging
import asyncpg

from mcp_server.db import get_pool

logger = logging.getLogger(__name__)


class BankingAPI:
    """Banking API client that queries PostgreSQL database."""
    
    async def get_accounts(self, user_id: str) -> List[Dict[str, Any]]:
        """
        Get all accounts for a user.
        
        Args:
            user_id: User identifier
            
        Returns:
            List of account dictionaries
        """
        pool = await get_pool()
        
        try:
            # Acquire connection from pool
            conn = await pool.acquire()
            try:
                rows = await conn.fetch("""
                    SELECT 
                        account_id,
                        account_type,
                        account_number,
                        balance,
                        credit_limit,
                        currency
                    FROM accounts
                    WHERE user_id = $1
                    ORDER BY account_type, account_id
                """, user_id)
                
                accounts = []
                for row in rows:
                    account = {
                        "type": row["account_type"],
                        "account_number": row["account_number"],
                        "balance": float(row["balance"]),
                        "currency": row.get("currency", "USD")
                    }
                    
                    # Add credit limit for credit cards
                    if row["account_type"] == "credit_card" and row["credit_limit"]:
                        account["limit"] = float(row["credit_limit"])
                    
                    accounts.append(account)
                
                logger.info(f"Retrieved {len(accounts)} accounts for user_id: {user_id}")
                return accounts
            finally:
                # Always release connection back to pool
                await pool.release(conn)
                
        except asyncpg.PostgresError as e:
            logger.error(f"Database error fetching accounts for user_id {user_id}: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error fetching accounts for user_id {user_id}: {e}")
            raise
    
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
        pool = await get_pool()
        
        try:
            # Acquire connection from pool
            conn = await pool.acquire()
            try:
                # Build query with filters using proper parameterized queries
                conditions = ["a.user_id = $1"]
                params = [user_id]
                param_index = 2
                
                # Add account_type filter
                if account_type:
                    conditions.append(f"a.account_type = ${param_index}")
                    params.append(account_type)
                    param_index += 1
                
                # Add date filters
                if start_date:
                    conditions.append(f"t.transaction_date >= ${param_index}::date")
                    params.append(start_date)
                    param_index += 1
                
                if end_date:
                    conditions.append(f"t.transaction_date <= ${param_index}::date")
                    params.append(end_date)
                    param_index += 1
                
                # Build final query
                where_clause = " AND ".join(conditions)
                limit_param = param_index
                query = f"""
                    SELECT 
                        t.transaction_id,
                        t.transaction_date,
                        t.description,
                        t.amount,
                        t.transaction_type,
                        a.account_number
                    FROM transactions t
                    INNER JOIN accounts a ON t.account_id = a.account_id
                    WHERE {where_clause}
                    ORDER BY t.transaction_date DESC, t.transaction_id DESC
                    LIMIT ${limit_param}
                """
                params.append(limit)
                
                rows = await conn.fetch(query, *params)
                
                transactions = []
                for row in rows:
                    transaction = {
                        "date": row["transaction_date"].strftime("%Y-%m-%d"),
                        "description": row["description"],
                        "amount": float(row["amount"]),
                        "type": row["transaction_type"],
                        "account_number": row["account_number"]
                    }
                    transactions.append(transaction)
                
                logger.info(
                    f"Retrieved {len(transactions)} transactions for user_id: {user_id}"
                )
                return transactions
            finally:
                # Always release connection back to pool
                await pool.release(conn)
                
        except asyncpg.PostgresError as e:
            logger.error(
                f"Database error fetching transactions for user_id {user_id}: {e}"
            )
            raise
        except Exception as e:
            logger.error(
                f"Unexpected error fetching transactions for user_id {user_id}: {e}"
            )
            raise
    
    async def get_loans(self, user_id: str) -> List[Dict[str, Any]]:
        """
        Get loans for a user.
        
        Args:
            user_id: User identifier
            
        Returns:
            List of loan dictionaries
        """
        pool = await get_pool()
        
        try:
            # Acquire connection from pool
            conn = await pool.acquire()
            try:
                rows = await conn.fetch("""
                    SELECT 
                        loan_id,
                        loan_type,
                        loan_account_number,
                        balance,
                        interest_rate,
                        monthly_payment,
                        remaining_term_months,
                        next_payment_date
                    FROM loans
                    WHERE user_id = $1
                    ORDER BY loan_type, loan_id
                """, user_id)
                
                loans = []
                for row in rows:
                    loan = {
                        "type": row["loan_type"],
                        "account_number": row["loan_account_number"],
                        "balance": float(row["balance"]),
                        "rate": float(row["interest_rate"]),
                        "monthly_payment": float(row["monthly_payment"])
                    }
                    
                    # Add optional fields
                    if row["remaining_term_months"]:
                        loan["remaining_term_months"] = row["remaining_term_months"]
                    
                    if row["next_payment_date"]:
                        loan["next_payment_date"] = row["next_payment_date"].strftime("%Y-%m-%d")
                    
                    loans.append(loan)
                
                logger.info(f"Retrieved {len(loans)} loans for user_id: {user_id}")
                return loans
            finally:
                # Always release connection back to pool
                await pool.release(conn)
                
        except asyncpg.PostgresError as e:
            logger.error(f"Database error fetching loans for user_id {user_id}: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error fetching loans for user_id {user_id}: {e}")
            raise
