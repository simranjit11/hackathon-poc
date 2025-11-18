"""
MCP Server - Banking Tools
===========================
Exposes hardened, JWT-authenticated banking tools using FASTMCP.
"""

from fastmcp import FastMCP
import logging
import sys
from typing import Optional, List

from mcp_server.config import settings
from mcp_server.auth import verify_jwt_token, User
from mcp_server.banking_api import BankingAPI
from mcp_server.cache import cache_manager
from mcp_server.masking import mask_account_number, mask_merchant_info

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Create FastMCP server instance
mcp = FastMCP(name="Banking Tools Server")


def get_user_from_token(jwt_token: str) -> User:
    """
    Extract and validate user from JWT token.
    
    Args:
        jwt_token: JWT token string
        
    Returns:
        User object with user_id and scopes
        
    Raises:
        ValueError: If token is invalid or missing required scope
    """
    payload = verify_jwt_token(jwt_token)
    user_id = payload.get("sub")
    scopes = payload.get("scopes", [])
    
    if "read" not in scopes:
        raise ValueError("Missing required 'read' scope")
    
    return User(user_id=user_id, scopes=scopes)


@mcp.tool()
async def get_balance(
    jwt_token: str,
    account_type: Optional[str] = None
) -> List[dict]:
    """
    Get account balances for the authenticated user.
    
    Args:
        jwt_token: JWT authentication token with 'read' scope
        account_type: Optional account type filter (checking, savings, credit_card)
        
    Returns:
        List of balance responses for all account types
    """
    logger.info("Balance request received")
    
    try:
        # Authenticate user
        user = get_user_from_token(jwt_token)
        logger.info(f"Balance request for user_id: {user.user_id}")
        
        # Check cache
        cache_key = f"balance:{user.user_id}:{account_type or 'all'}"
        cached_result = await cache_manager.get(cache_key)
        if cached_result:
            logger.info(f"Returning cached balance for user_id: {user.user_id}")
            return cached_result
        
        # Query banking API
        banking_api = BankingAPI()
        accounts = await banking_api.get_accounts(user.user_id)
        
        # Filter by account_type if specified
        if account_type:
            accounts = [
                acc for acc in accounts
                if acc.get("type", "").lower() == account_type.lower()
            ]
        
        # Build response with masking
        balances = []
        for account in accounts:
            acc_type = account.get("type", "unknown")
            acc_number = account.get("account_number", "")
            balance = account.get("balance", 0.0)
            
            response = {
                "account_type": acc_type,
                "account_number": mask_account_number(acc_number),
                "balance": balance,
                "currency": "USD"
            }
            
            # Add credit card specific fields
            if acc_type == "credit_card":
                response["credit_limit"] = account.get("limit", 0.0)
                response["available_credit"] = account.get("limit", 0.0) - balance
            
            balances.append(response)
        
        # Cache results (5 minute TTL)
        await cache_manager.set(cache_key, balances, ttl=300)
        
        logger.info(
            f"Balance retrieved for user_id: {user.user_id}, "
            f"accounts: {len(balances)}"
        )
        
        return balances
        
    except ValueError as e:
        logger.warning(f"Authentication error: {e}")
        raise ValueError(f"Authentication failed: {str(e)}")
    except Exception as e:
        logger.error(f"Error retrieving balance: {e}")
        raise ValueError(f"Failed to retrieve account balances: {str(e)}")


@mcp.tool()
async def get_transactions(
    jwt_token: str,
    account_type: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    limit: int = 10
) -> List[dict]:
    """
    Get transaction history for the authenticated user.
    
    Args:
        jwt_token: JWT authentication token with 'read' scope
        account_type: Optional account type filter
        start_date: Optional start date filter (YYYY-MM-DD)
        end_date: Optional end date filter (YYYY-MM-DD)
        limit: Maximum number of transactions (default: 10, max: 100)
        
    Returns:
        List of transaction responses, sorted by date (most recent first)
    """
    logger.info("Transaction request received")
    
    try:
        # Authenticate user
        user = get_user_from_token(jwt_token)
        logger.info(
            f"Transaction request for user_id: {user.user_id}, "
            f"limit: {limit}"
        )
        
        # Validate limit
        limit = max(1, min(100, limit))
        
        # Build cache key
        cache_key = (
            f"transactions:{user.user_id}:"
            f"{account_type or 'all'}:"
            f"{start_date or 'none'}:"
            f"{end_date or 'none'}:"
            f"{limit}"
        )
        
        # Check cache
        cached_result = await cache_manager.get(cache_key)
        if cached_result:
            logger.info(f"Returning cached transactions for user_id: {user.user_id}")
            return cached_result
        
        # Query banking API
        banking_api = BankingAPI()
        transactions = await banking_api.get_transactions(
            user.user_id,
            account_type=account_type,
            start_date=start_date,
            end_date=end_date,
            limit=limit
        )
        
        # Build response with masking
        responses = []
        for txn in transactions:
            response = {
                "date": txn.get("date", ""),
                "description": mask_merchant_info(txn.get("description", "")),
                "amount": txn.get("amount", 0.0),
                "type": txn.get("type", "debit"),
                "account_number": mask_account_number(
                    txn.get("account_number", "")
                )
            }
            responses.append(response)
        
        # Sort by date (most recent first)
        responses.sort(key=lambda x: x["date"], reverse=True)
        
        # Cache results (2 minute TTL)
        await cache_manager.set(cache_key, responses, ttl=120)
        
        logger.info(
            f"Transactions retrieved for user_id: {user.user_id}, "
            f"count: {len(responses)}"
        )
        
        return responses
        
    except ValueError as e:
        logger.warning(f"Authentication error: {e}")
        raise ValueError(f"Authentication failed: {str(e)}")
    except Exception as e:
        logger.error(f"Error retrieving transactions: {e}")
        raise ValueError(f"Failed to retrieve transactions: {str(e)}")


@mcp.tool()
async def get_loans(jwt_token: str) -> List[dict]:
    """
    Get loan information for the authenticated user.
    
    Args:
        jwt_token: JWT authentication token with 'read' scope
        
    Returns:
        List of loan responses with details and payment schedules
    """
    logger.info("Loan request received")
    
    try:
        # Authenticate user
        user = get_user_from_token(jwt_token)
        logger.info(f"Loan request for user_id: {user.user_id}")
        
        # Check cache
        cache_key = f"loans:{user.user_id}"
        cached_result = await cache_manager.get(cache_key)
        if cached_result:
            logger.info(f"Returning cached loans for user_id: {user.user_id}")
            return cached_result
        
        # Query banking API
        banking_api = BankingAPI()
        loans = await banking_api.get_loans(user.user_id)
        
        # Build response with masking
        responses = []
        for loan in loans:
            response = {
                "loan_type": loan.get("type", "Unknown"),
                "loan_account_number": mask_account_number(
                    loan.get("account_number", "")
                ),
                "balance": loan.get("balance", 0.0),
                "interest_rate": loan.get("rate", 0.0),
                "monthly_payment": loan.get("monthly_payment", 0.0),
                "remaining_term_months": loan.get("remaining_term_months"),
                "next_payment_date": loan.get("next_payment_date")
            }
            responses.append(response)
        
        # Cache results (10 minute TTL)
        await cache_manager.set(cache_key, responses, ttl=600)
        
        logger.info(
            f"Loans retrieved for user_id: {user.user_id}, "
            f"count: {len(responses)}"
        )
        
        return responses
        
    except ValueError as e:
        logger.warning(f"Authentication error: {e}")
        raise ValueError(f"Authentication failed: {str(e)}")
    except Exception as e:
        logger.error(f"Error retrieving loans: {e}")
        raise ValueError(f"Failed to retrieve loan information: {str(e)}")


if __name__ == "__main__":
    logger.info(
        f"Starting MCP Banking Tools Server with HTTP transport "
        f"on {settings.HOST}:{settings.PORT}{settings.MCP_PATH}"
    )
    
    # Note: Database connection pool will be created lazily on first use
    # in the correct event loop context
    
    mcp.run(
        transport="streamable-http",
        host=settings.HOST,
        port=settings.PORT,
        path=settings.MCP_PATH,
        stateless_http=True
    )
