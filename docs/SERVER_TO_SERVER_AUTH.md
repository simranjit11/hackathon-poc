# Server-to-Server Authentication Guide

## Overview

This document describes the API key-based authentication mechanism for server-to-server communication between the MCP server and the backend API (Next.js).

## Architecture

```
┌─────────────┐                    ┌──────────────┐
│  MCP Server │───API Key Auth───►│ Backend API  │
│  (FastAPI)  │                    │  (Next.js)   │
└─────────────┘                    └──────────────┘
     │                                      │
     │ GET /api/internal/users/{user_id}   │
     │ Headers: X-API-Key: <api_key>       │
     │                                      │
     └──────────────────────────────────────┘
```

## Why API Key Authentication?

**For server-to-server communication:**
- ✅ Simple and efficient
- ✅ No token expiration overhead
- ✅ Suitable for backend services
- ✅ Easy to rotate/revoke
- ✅ Lower latency than JWT validation

**Security Considerations:**
- API keys are stored in environment variables (never in code)
- Keys should be long, random strings
- Rotate keys periodically
- Use HTTPS in production
- Monitor API key usage

## Implementation

### Backend API Endpoint

**Endpoint:** `GET /api/internal/users/[user_id]`

**Authentication:** API Key via `X-API-Key` header

**Request:**
```http
GET /api/internal/users/12345
X-API-Key: your-secret-api-key-here
```

**Response:**
```json
{
  "user": {
    "id": "12345",
    "email": "user@example.com",
    "name": "John Doe",
    "roles": ["customer"],
    "permissions": ["read", "transact", "configure"],
    "createdAt": "2025-01-01T00:00:00.000Z",
    "lastLoginAt": "2025-01-15T10:30:00.000Z"
  }
}
```

**Error Responses:**
- `401 Unauthorized`: Invalid or missing API key
- `404 Not Found`: User not found
- `500 Internal Server Error`: Server error

### MCP Server Client

**File:** `mcp-server/backend_client.py`

**Usage:**
```python
from backend_client import get_backend_client

# Get singleton client instance
backend_client = get_backend_client()

# Fetch user details
user_details = await backend_client.get_user_details("12345")
print(user_details["email"])  # user@example.com
print(user_details["name"])   # John Doe
```

**Features:**
- Singleton pattern for connection reuse
- Automatic API key injection
- Error handling with fallback to mock data
- Async HTTP client with timeout

## Configuration

### Environment Variables

**Backend API (Next.js):**
```bash
# .env.local
INTERNAL_API_KEY=your-secret-api-key-change-in-production
```

**MCP Server:**
```bash
# .env
INTERNAL_API_KEY=your-secret-api-key-change-in-production  # Must match backend
BACKEND_API_URL=http://localhost:3000  # Backend API base URL
```

**⚠️ CRITICAL:** `INTERNAL_API_KEY` must match in both services!

## Security Best Practices

### 1. Generate Strong API Keys

```bash
# Generate a secure random API key
openssl rand -hex 32
# Output: a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0u1v2w3x4y5z6
```

### 2. Store Keys Securely

- ✅ Use environment variables
- ✅ Never commit keys to git
- ✅ Use secrets management in production (AWS Secrets Manager, HashiCorp Vault, etc.)
- ❌ Don't hardcode keys
- ❌ Don't log keys

### 3. Rotate Keys Periodically

- Rotate keys every 90 days (or per your security policy)
- Update both services simultaneously
- Monitor for failed authentication attempts

### 4. Monitor Usage

- Log all API key authentication attempts
- Alert on repeated failures
- Track usage patterns

## Example Integration

### In MCP Server Tools

```python
# mcp-server/main.py
from backend_client import get_backend_client

@mcp.tool()
async def get_balance(jwt_token: str, account_type: Optional[str] = None):
    # Authenticate user via JWT
    user = get_user_from_token(jwt_token)
    
    # Get user details from backend API (using API key)
    backend_client = get_backend_client()
    try:
        user_details = await backend_client.get_user_details(user.user_id)
        customer_name = user_details.get("name") or user_details.get("email")
    except Exception as e:
        logger.warning(f"Failed to fetch user details: {e}")
        customer_name = "Customer"  # Fallback
    
    # Use customer_name in response
    return {
        "message": f"Hello {customer_name}! Your balance is..."
    }
```

## Testing

### Test Backend API Endpoint

```bash
# Set API key
export INTERNAL_API_KEY="test-api-key-12345"

# Test endpoint
curl -X GET http://localhost:3000/api/internal/users/12345 \
  -H "X-API-Key: test-api-key-12345"
```

**Expected Response:**
```json
{
  "user": {
    "id": "12345",
    "email": "user@example.com",
    "name": "John Doe",
    ...
  }
}
```

### Test MCP Server Client

```python
# In MCP server
from backend_client import get_backend_client

async def test():
    client = get_backend_client()
    user = await client.get_user_details("12345")
    print(user)
```

### Test Authentication Failure

```bash
# Missing API key
curl -X GET http://localhost:3000/api/internal/users/12345
# Expected: 401 Unauthorized

# Invalid API key
curl -X GET http://localhost:3000/api/internal/users/12345 \
  -H "X-API-Key: wrong-key"
# Expected: 401 Unauthorized
```

## Comparison: API Key vs JWT for Server-to-Server

| Aspect | API Key | JWT |
|--------|---------|-----|
| **Complexity** | Simple | More complex |
| **Overhead** | Low | Higher (signature verification) |
| **Expiration** | Manual rotation | Built-in expiration |
| **Use Case** | Server-to-server | User authentication |
| **Security** | Good (with HTTPS) | Excellent (with signing) |
| **Latency** | Lower | Slightly higher |

**Recommendation:** API keys are perfect for server-to-server communication where:
- Services are trusted
- No user context needed
- Simple authentication is sufficient
- Performance matters

## Troubleshooting

### Issue: "Invalid or missing API key"

**Causes:**
1. `INTERNAL_API_KEY` not set in environment
2. API key mismatch between services
3. Header name incorrect (should be `X-API-Key`)

**Fix:**
```bash
# Check environment variables
echo $INTERNAL_API_KEY

# Verify keys match in both services
# Backend: .env.local
# MCP Server: .env
```

### Issue: "Failed to connect to backend API"

**Causes:**
1. Backend API not running
2. Wrong `BACKEND_API_URL`
3. Network/firewall issues

**Fix:**
```bash
# Check backend is running
curl http://localhost:3000/api/health

# Verify BACKEND_API_URL
echo $BACKEND_API_URL
```

### Issue: "User not found"

**Causes:**
1. User ID doesn't exist in database
2. Database connection issue

**Fix:**
```bash
# Check user exists
# In backend, query database or check /api/auth/me endpoint
```

## Next Steps

1. ✅ API key authentication implemented
2. ✅ Backend endpoint created (`/api/internal/users/[user_id]`)
3. ✅ MCP server client created
4. ⚠️ Configure environment variables
5. ⚠️ Test end-to-end flow
6. ⚠️ Add phone number field to User schema (if needed)
7. ⚠️ Add more internal endpoints as needed

---

## Summary

**API key authentication is perfect for server-to-server communication** because:
- Simple and efficient
- No token expiration overhead
- Suitable for trusted backend services
- Easy to implement and maintain

The implementation provides:
- Secure API key validation
- Error handling with fallback
- Singleton client pattern
- Comprehensive error messages

