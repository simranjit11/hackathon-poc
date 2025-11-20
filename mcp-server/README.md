# MCP Banking Tools Server

JWT-authenticated banking tools server using FASTMCP that integrates with the Next.js banking API backend.

## Features

- **Balance Lookup**: Get account balances for all account types
- **Transaction History**: Retrieve recent transactions with filtering
- **Loan Information**: Get loan details and payment schedules
- **Payment Processing**: Initiate and confirm payments (two-step process)
- **Alert Management**: Set up and retrieve payment alerts
- **JWT Authentication**: Secure token-based authentication with scope validation
- **Data Masking**: Sensitive information masked before returning results
- **Caching**: Redis-based caching with configurable TTL
- **HTTP API Integration**: Calls Next.js banking APIs instead of direct database access

## Architecture

The MCP server acts as a middleware layer that:
1. Receives MCP tool calls with JWT tokens
2. Validates and authenticates JWT tokens
3. Makes HTTP requests to the Next.js banking API backend
4. Applies data masking and caching
5. Returns formatted responses to the MCP client

## Installation

```bash
# Using uv (recommended)
uv sync

# Or using pip
pip install -e .
```

## Configuration

Set environment variables:

```bash
# Backend API (Next.js server)
BACKEND_API_URL=http://localhost:3000
INTERNAL_API_KEY=your-internal-api-key  # For server-to-server calls

# JWT
MCP_JWT_SECRET_KEY=your-secret-key
MCP_JWT_ISSUER=orchestrator

# Server
MCP_HOST=0.0.0.0
MCP_PORT=8001
MCP_PATH=/mcp

# Cache (Redis)
CACHE_ENABLED=true
REDIS_URL=redis://localhost:6379/0

# Logging
LOG_LEVEL=INFO
```

## Running

The server uses HTTP transport by default:

```bash
# Using uv
uv run main.py

# Or using Python directly
python main.py
```

The server will be available at `http://{HOST}:{PORT}{MCP_PATH}` (default: `http://0.0.0.0:8001/mcp`)

## Transport Configuration

The server uses **streamable HTTP transport** by default. You can configure it via environment variables:

- `MCP_HOST`: Server host (default: `0.0.0.0`)
- `MCP_PORT`: Server port (default: `8001`)
- `MCP_PATH`: MCP endpoint path (default: `/mcp`)

## Tools

All tools require a `jwt_token` parameter as the first argument.

### get_balance

Get account balances for the authenticated user.

**Parameters:**
- `jwt_token` (str, required): JWT authentication token with 'read' scope
- `account_type` (str, optional): Account type filter (checking, savings, credit_card)

**Returns:** List of balance responses

### get_transactions

Get transaction history for the authenticated user.

**Parameters:**
- `jwt_token` (str, required): JWT authentication token with 'read' scope
- `account_type` (str, optional): Account type filter
- `start_date` (str, optional): Start date filter (YYYY-MM-DD)
- `end_date` (str, optional): End date filter (YYYY-MM-DD)
- `limit` (int): Maximum number of transactions (default: 10, max: 100)

**Returns:** List of transaction responses, sorted by date (most recent first)

### get_loans

Get loan information for the authenticated user.

**Parameters:**
- `jwt_token` (str, required): JWT authentication token with 'read' scope

**Returns:** List of loan responses with details and payment schedules

### make_payment

Make a payment or transfer between accounts (two-step process: initiate then confirm).

**Parameters:**
- `jwt_token` (str, required): JWT authentication token with 'transact' scope
- `from_account` (str, required): Source account type ('checking', 'savings')
- `to_account` (str, required): Destination account or payee name
- `amount` (float, required): Amount to transfer
- `description` (str, optional): Optional description for the transaction

**Returns:** Payment confirmation with details

### get_credit_limit

Get credit card limits and available credit.

**Parameters:**
- `jwt_token` (str, required): JWT authentication token with 'read' scope

**Returns:** Credit card information with limits and utilization

### set_alert

Set up payment reminders or alerts.

**Parameters:**
- `jwt_token` (str, required): JWT authentication token with 'configure' scope
- `alert_type` (str, required): Type of alert ('payment', 'low_balance', 'large_transaction')
- `description` (str, required): Description of the alert
- `due_date` (str, optional): Optional due date for payment reminders (YYYY-MM-DD)

**Returns:** Alert confirmation

### get_alerts

Get active payment alerts and reminders.

**Parameters:**
- `jwt_token` (str, required): JWT authentication token with 'read' scope

**Returns:** List of active alerts

### get_user_details

Get user profile details including email, name, roles, and permissions.

**Parameters:**
- `jwt_token` (str, required): JWT authentication token with 'read' scope

**Returns:** Dictionary with user details

### get_transfer_contacts

Get list of saved contacts/beneficiaries for transfers.

**Parameters:**
- `jwt_token` (str, required): JWT authentication token with 'read' scope

**Returns:** List of beneficiary dictionaries with nickname and payment details

### get_current_date_time

Get the current date and time.

**Parameters:**
- `jwt_token` (str, required): JWT authentication token with 'read' scope

**Returns:** Formatted current date and time string

## Authentication

All tools require a JWT token as the first parameter. The token must:
- Be signed with the configured `MCP_JWT_SECRET_KEY`
- Have issuer matching `MCP_JWT_ISSUER`
- Include appropriate scope ('read', 'transact', or 'configure') in the `scopes` claim
- Include `sub` claim with user identifier

Generate tokens using:
```bash
uv run python generate_jwt.py
```

## Caching

The server uses Redis for caching:
- Balance results: 5 minutes TTL
- Transaction results: 2 minutes TTL
- Loan results: 10 minutes TTL

Configure Redis via `REDIS_URL` environment variable.

## Integration with Next.js Backend

The MCP server integrates with the Next.js banking API backend:

- **User-authenticated calls**: Uses JWT tokens passed from MCP tools
- **Server-to-server calls**: Uses `INTERNAL_API_KEY` for internal endpoints
- **API endpoints**: Calls `/api/banking/*` endpoints on the Next.js server

See `INTEGRATION_NOTES.md` and `INTEGRATION_SUMMARY.md` for detailed integration information.

## Troubleshooting

### Backend API Connection Issues

If you get connection errors, check:

1. **Next.js server is running:**
   ```bash
   curl http://localhost:3000/api/health
   ```

2. **Backend URL is correct:**
   ```bash
   echo $BACKEND_API_URL
   # Should be: http://localhost:3000
   ```

3. **Internal API key is configured:**
   ```bash
   echo $INTERNAL_API_KEY
   # Should match the key configured in Next.js backend
   ```

### JWT Token Issues

1. **Token is valid:**
   - Check that `MCP_JWT_SECRET_KEY` matches the key used to sign tokens
   - Verify `MCP_JWT_ISSUER` matches the token issuer

2. **Token has required scopes:**
   - 'read' scope for read operations
   - 'transact' scope for payment operations
   - 'configure' scope for alert configuration

### Redis Connection Issues

If caching is not working:

1. **Redis is running:**
   ```bash
   redis-cli ping
   # Should return: PONG
   ```

2. **Redis URL is correct:**
   ```bash
   echo $REDIS_URL
   # Should be: redis://localhost:6379/0
   ```
