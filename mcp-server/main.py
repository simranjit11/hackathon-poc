"""
MCP Server - Banking Tools
===========================
Exposes hardened, JWT-authenticated banking tools using FASTMCP.
"""

from fastmcp import FastMCP
from fastmcp.server.dependencies import get_http_headers
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


def get_user_from_token(jwt_token: str, required_scope: str = "read") -> User:
    """
    Extract and validate user from JWT token in HTTP headers.
    
    Looks for JWT token in:
    1. Authorization header: "Bearer <token>"
    2. X-JWT-Token header: "<token>"
    
    Args:
        jwt_token: JWT token string
        required_scope: Required scope (default: "read")
        
    Returns:
        User object with user_id and scopes
        
    Raises:
        ValueError: If token is invalid, missing, or missing required scope
    """
    headers = get_http_headers()
    
    # Try Authorization header first (Bearer token)
    jwt_token = None
    auth_header = headers.get("authorization", "")
    if auth_header.startswith("Bearer "):
        jwt_token = auth_header[7:].strip()
    elif auth_header.startswith("bearer "):
        jwt_token = auth_header[7:].strip()
    
    # Fallback to X-JWT-Token header
    if not jwt_token:
        jwt_token = headers.get("x-jwt-token") or headers.get("X-JWT-Token")
    
    if not jwt_token:
        raise ValueError("Missing JWT token in Authorization or X-JWT-Token header")
    
    payload = verify_jwt_token(jwt_token)
    user_id = payload.get("sub")
    scopes = payload.get("scopes", [])
    
    if required_scope not in scopes:
        raise ValueError(f"Missing required '{required_scope}' scope")
    
    return User(user_id=user_id, scopes=scopes)


@mcp.tool()
async def get_balance(
    account_type: Optional[str] = None
) -> List[dict]:
    """
    Get account balances for the authenticated user.
    
    Args:
        account_type: Optional account type filter (checking, savings, credit_card)
        
    Returns:
        List of balance responses for all account types
    """
    logger.info("Balance request received")
    
    try:
        # Authenticate user from HTTP headers
        user = get_user_from_headers()
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
    account_type: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    limit: int = 10
) -> List[dict]:
    """
    Get transaction history for the authenticated user.
    
    Args:
        account_type: Optional account type filter
        start_date: Optional start date filter (YYYY-MM-DD)
        end_date: Optional end date filter (YYYY-MM-DD)
        limit: Maximum number of transactions (default: 10, max: 100)
        
    Returns:
        List of transaction responses, sorted by date (most recent first)
    """
    logger.info("Transaction request received")
    
    try:
        # Authenticate user from HTTP headers
        user = get_user_from_headers()
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
async def get_loans() -> List[dict]:
    """
    Get loan information for the authenticated user.
    
    Returns:
        List of loan responses with details and payment schedules
    """
    logger.info("Loan request received")
    
    try:
        # Authenticate user from HTTP headers
        user = get_user_from_headers()
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


@mcp.tool()
async def make_payment(
    jwt_token: str,
    from_account: str,
    to_account: str,
    amount: float,
    description: str = ""
) -> dict:
    """
    Make a payment or transfer between accounts.
    
    Args:
        jwt_token: JWT authentication token with 'transact' scope
        from_account: Source account type ('checking', 'savings')
        to_account: Destination account or payee name
        amount: Amount to transfer
        description: Optional description for the transaction
        
    Returns:
        Payment confirmation with details
    """
    logger.info("Payment request received")
    
    try:
        # Authenticate user with transact scope
        user = get_user_from_token(jwt_token, required_scope="transact")
        logger.info(
            f"Payment request for user_id: {user.user_id}, "
            f"from: {from_account}, to: {to_account}, amount: {amount}"
        )
        
        # Query banking API
        banking_api = BankingAPI()
        result = await banking_api.make_payment(
            user.user_id,
            from_account,
            to_account,
            amount,
            description
        )
        
        logger.info(
            f"Payment successful for user_id: {user.user_id}, "
            f"confirmation: {result['confirmation_number']}"
        )
        
        return result
        
    except ValueError as e:
        logger.warning(f"Payment error: {e}")
        raise ValueError(f"Payment failed: {str(e)}")
    except Exception as e:
        logger.error(f"Error processing payment: {e}")
        raise ValueError(f"Failed to process payment: {str(e)}")


@mcp.tool()
async def get_credit_limit(jwt_token: str) -> dict:
    """
    Get credit card limits and available credit for the authenticated user.
    
    Args:
        jwt_token: JWT authentication token with 'read' scope
        
    Returns:
        Credit card information with limits and utilization
    """
    logger.info("Credit limit request received")
    
    try:
        # Authenticate user
        user = get_user_from_token(jwt_token)
        logger.info(f"Credit limit request for user_id: {user.user_id}")
        
        # Get balances (specifically credit card)
        banking_api = BankingAPI()
        accounts = await banking_api.get_accounts(user.user_id)
        
        # Find credit card account
        credit_card = None
        for account in accounts:
            if account.get("type") == "credit_card":
                credit_card = account
                break
        
        if not credit_card:
            customer_name = await banking_api.get_customer_name(user.user_id) or "Customer"
            return {
                "has_credit_card": False,
                "message": f"Hello {customer_name}! You don't have a credit card account with us."
            }
        
        balance = credit_card.get("balance", 0.0)
        limit = credit_card.get("limit", 0.0)
        available_credit = limit - balance
        utilization = (balance / limit * 100) if limit > 0 else 0
        
        result = {
            "has_credit_card": True,
            "credit_limit": limit,
            "current_balance": balance,
            "available_credit": available_credit,
            "credit_utilization_percent": round(utilization, 1),
            "account_number": mask_account_number(credit_card.get("account_number", ""))
        }
        
        logger.info(
            f"Credit limit retrieved for user_id: {user.user_id}, "
            f"utilization: {utilization:.1f}%"
        )
        
        return result
        
    except ValueError as e:
        logger.warning(f"Authentication error: {e}")
        raise ValueError(f"Authentication failed: {str(e)}")
    except Exception as e:
        logger.error(f"Error retrieving credit limit: {e}")
        raise ValueError(f"Failed to retrieve credit limit: {str(e)}")


@mcp.tool()
async def set_alert(
    jwt_token: str,
    alert_type: str,
    description: str,
    due_date: str = ""
) -> dict:
    """
    Set up payment reminders or alerts.
    
    Args:
        jwt_token: JWT authentication token with 'configure' scope
        alert_type: Type of alert ('payment', 'low_balance', 'large_transaction')
        description: Description of the alert
        due_date: Optional due date for payment reminders (YYYY-MM-DD)
        
    Returns:
        Alert confirmation
    """
    logger.info("Set alert request received")
    
    try:
        # Authenticate user with configure scope
        user = get_user_from_token(jwt_token, required_scope="configure")
        logger.info(
            f"Set alert request for user_id: {user.user_id}, "
            f"type: {alert_type}"
        )
        
        # Query banking API
        banking_api = BankingAPI()
        alert = await banking_api.set_alert(
            user.user_id,
            alert_type,
            description,
            due_date if due_date else None
        )
        
        customer_name = await banking_api.get_customer_name(user.user_id) or "Customer"
        
        result = {
            "success": True,
            "customer_name": customer_name,
            "alert": alert,
            "message": f"Reminder set successfully for {customer_name}!"
        }
        
        logger.info(f"Alert set for user_id: {user.user_id}, type: {alert_type}")
        
        return result
        
    except ValueError as e:
        logger.warning(f"Authentication error: {e}")
        raise ValueError(f"Authentication failed: {str(e)}")
    except Exception as e:
        logger.error(f"Error setting alert: {e}")
        raise ValueError(f"Failed to set alert: {str(e)}")


@mcp.tool()
async def get_alerts(jwt_token: str) -> List[dict]:
    """
    Get active payment alerts and reminders for the authenticated user.
    
    Args:
        jwt_token: JWT authentication token with 'read' scope
        
    Returns:
        List of active alerts
    """
    logger.info("Get alerts request received")
    
    try:
        # Authenticate user
        user = get_user_from_token(jwt_token)
        logger.info(f"Get alerts request for user_id: {user.user_id}")
        
        # Query banking API
        banking_api = BankingAPI()
        alerts = await banking_api.get_alerts(user.user_id)
        customer_name = await banking_api.get_customer_name(user.user_id) or "Customer"
        
        if not alerts:
            return [{
                "customer_name": customer_name,
                "has_alerts": False,
                "message": f"Hello {customer_name}! You have no active alerts or reminders set up."
            }]
        
        # Format alerts
        result = []
        for alert in alerts:
            status = "🟢 Active" if alert.get("active", False) else "🔴 Inactive"
            result.append({
                "customer_name": customer_name,
                "has_alerts": True,
                "type": alert.get("type", ""),
                "description": alert.get("description", ""),
                "status": status,
                "created_at": alert.get("created_at", "")
            })
        
        logger.info(
            f"Alerts retrieved for user_id: {user.user_id}, "
            f"count: {len(result)}"
        )
        
        return result
        
    except ValueError as e:
        logger.warning(f"Authentication error: {e}")
        raise ValueError(f"Authentication failed: {str(e)}")
    except Exception as e:
        logger.error(f"Error retrieving alerts: {e}")
        raise ValueError(f"Failed to retrieve alerts: {str(e)}")


@mcp.tool()
async def get_interest_rates(jwt_token: str) -> str:
    """
    Get current interest rates for various banking products.
    
    Args:
        jwt_token: JWT authentication token with 'read' scope
        
    Returns:
        Formatted string with interest rates
    """
    logger.info("Interest rates request received")
    
    try:
        # Authenticate user
        user = get_user_from_token(jwt_token)
        logger.info(f"Interest rates request for user_id: {user.user_id}")
        
        # Return static interest rates (mock data)
        return """Current Interest Rates (as of November 2025):

💰 DEPOSIT ACCOUNTS:
• Checking Account: 0.10% APY
• Savings Account: 4.25% APY
• Money Market: 4.50% APY
• 12-Month CD: 5.00% APY
• 24-Month CD: 4.75% APY

💳 CREDIT PRODUCTS:
• Credit Cards: 15.99% - 24.99% APR
• Personal Loans: 5.99% - 18.99% APR
• Auto Loans: 3.49% - 8.99% APR
• Home Equity Line: 7.25% - 9.50% APR

🏠 MORTGAGE RATES:
• 30-Year Fixed: 7.125% APR
• 15-Year Fixed: 6.625% APR
• 5/1 ARM: 6.250% APR

Rates are subject to change and based on creditworthiness. Contact us for personalized rates!"""
        
    except ValueError as e:
        logger.warning(f"Authentication error: {e}")
        raise ValueError(f"Authentication failed: {str(e)}")
    except Exception as e:
        logger.error(f"Error retrieving interest rates: {e}")
        raise ValueError(f"Failed to retrieve interest rates: {str(e)}")


@mcp.tool()
async def get_current_date_time(jwt_token: str) -> str:
    """
    Get the current date and time.
    
    Args:
        jwt_token: JWT authentication token with 'read' scope
        
    Returns:
        Formatted current date and time string
    """
    logger.info("Date/time request received")
    
    try:
        # Authenticate user
        user = get_user_from_token(jwt_token)
        
        from datetime import datetime
        current_datetime = datetime.now().strftime("%B %d, %Y at %I:%M %p")
        return f"The current date and time is {current_datetime}"
        
    except ValueError as e:
        logger.warning(f"Authentication error: {e}")
        raise ValueError(f"Authentication failed: {str(e)}")
    except Exception as e:
        logger.error(f"Error retrieving date/time: {e}")
        raise ValueError(f"Failed to retrieve date/time: {str(e)}")


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
