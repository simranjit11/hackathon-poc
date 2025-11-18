# MCP Banking Tools Server

JWT-authenticated banking tools server using FASTMCP with PostgreSQL backend.

## Features

- **Balance Lookup**: Get account balances for all account types
- **Transaction History**: Retrieve recent transactions with filtering
- **Loan Information**: Get loan details and payment schedules
- **JWT Authentication**: Secure token-based authentication with scope validation
- **Data Masking**: Sensitive information masked before returning results
- **Caching**: In-memory caching with configurable TTL
- **PostgreSQL Backend**: Real database queries instead of mock data

## Installation

```bash
pip install -e .
# or
uv sync
```

## Database Setup

### Option 1: Using Docker (Recommended)

If you have Docker installed, the easiest way is to use the setup script:

```bash
./setup-database.sh
```

Or manually:

```bash
# Start PostgreSQL container
docker run --name postgres-banking \
  -e POSTGRES_PASSWORD=postgres \
  -e POSTGRES_DB=banking \
  -p 5432:5432 \
  -d postgres:15

# Wait a few seconds for PostgreSQL to start, then run schema
docker exec -i postgres-banking psql -U postgres -d banking < schema.sql
```

### Option 2: Install PostgreSQL Locally

**macOS (using Homebrew):**
```bash
brew install postgresql@15
brew services start postgresql@15

# Create database
psql postgres -c "CREATE DATABASE banking;"

# Run schema
psql banking < schema.sql
```

**Linux (Ubuntu/Debian):**
```bash
sudo apt-get update
sudo apt-get install postgresql postgresql-contrib

# Create database
sudo -u postgres psql -c "CREATE DATABASE banking;"

# Run schema
sudo -u postgres psql banking < schema.sql
```

### Option 3: Use Cloud PostgreSQL

You can use any PostgreSQL service (AWS RDS, Google Cloud SQL, etc.) and set the `DATABASE_URL` environment variable.

## Configuration

Set environment variables:

```bash
# Database (required)
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/banking

# JWT
MCP_JWT_SECRET_KEY=your-secret-key
MCP_JWT_ISSUER=orchestrator

# Server
MCP_HOST=0.0.0.0
MCP_PORT=8001
MCP_PATH=/mcp

# Logging
LOG_LEVEL=INFO
```

## Running

The server uses HTTP transport by default:

```bash
python main.py
```

Or using FASTMCP CLI:

```bash
fastmcp run main.py
```

The server will be available at `http://{HOST}:{PORT}{MCP_PATH}` (default: `http://0.0.0.0:8001/mcp`)

## Transport Configuration

The server uses **streamable HTTP transport** by default. You can configure it via environment variables:

- `MCP_HOST`: Server host (default: `0.0.0.0`)
- `MCP_PORT`: Server port (default: `8001`)
- `MCP_PATH`: MCP endpoint path (default: `/mcp`)

## Database Schema

The database includes three main tables:

- **accounts**: User accounts (checking, savings, credit_card)
- **transactions**: Transaction history linked to accounts
- **loans**: Loan information for users

See `schema.sql` for the complete schema definition and sample data.

## Tools

### get_balance

Get account balances for the authenticated user.

**Parameters:**
- `account_type` (str, optional): Account type filter (checking, savings, credit_card)

**Returns:** List of balance responses

**Authentication:** JWT token must be provided in HTTP headers:
- `Authorization: Bearer <token>` (preferred)
- `X-JWT-Token: <token>` (fallback)

### get_transactions

Get transaction history for the authenticated user.

**Parameters:**
- `account_type` (str, optional): Account type filter
- `start_date` (str, optional): Start date filter (YYYY-MM-DD)
- `end_date` (str, optional): End date filter (YYYY-MM-DD)
- `limit` (int): Maximum number of transactions (default: 10, max: 100)

**Returns:** List of transaction responses, sorted by date (most recent first)

**Authentication:** JWT token must be provided in HTTP headers (see get_balance)

### get_loans

Get loan information for the authenticated user.

**Parameters:** None

**Returns:** List of loan responses with details and payment schedules

**Authentication:** JWT token must be provided in HTTP headers (see get_balance)

## Authentication

All tools require a JWT token with the 'read' scope in HTTP headers. The token must:
- Be signed with the configured `MCP_JWT_SECRET_KEY`
- Have issuer matching `MCP_JWT_ISSUER`
- Include 'read' in the `scopes` claim
- Include `sub` claim with user identifier

Generate tokens using:
```bash
uv run python generate_jwt.py
```

## Caching

- Balance results: 5 minutes TTL
- Transaction results: 2 minutes TTL
- Loan results: 10 minutes TTL

## Database Connection Pool

The server uses asyncpg connection pooling for efficient database access:
- Minimum pool size: 5 (configurable via `DATABASE_POOL_MIN_SIZE`)
- Maximum pool size: 20 (configurable via `DATABASE_POOL_MAX_SIZE`)

## Troubleshooting

### Database Connection Issues

If you get connection errors, check:

1. **PostgreSQL is running:**
   ```bash
   # Docker
   docker ps | grep postgres
   
   # Local
   brew services list | grep postgresql
   ```

2. **Connection string is correct:**
   ```bash
   echo $DATABASE_URL
   # Should be: postgresql://user:password@host:port/database
   ```

3. **Database exists:**
   ```bash
   # Docker
   docker exec -it postgres-banking psql -U postgres -l
   
   # Local
   psql -l
   ```

### Docker Container Management

```bash
# Start container
docker start postgres-banking

# Stop container
docker stop postgres-banking

# View logs
docker logs postgres-banking

# Remove container (WARNING: deletes data)
docker rm -f postgres-banking
```
