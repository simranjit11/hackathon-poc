# MCP Server Token Flow Architecture Review

**Date:** 2025-01-XX  
**Reviewer:** Winston (Architect)  
**Status:** Architecture Verification & Gap Analysis

---

## Executive Summary

This document reviews the MCP server implementation and token flow architecture to verify alignment with the initial architecture design. The review identifies several **critical gaps** that need to be addressed before production deployment.

---

## Architecture Alignment Analysis

### ✅ **What's Correctly Implemented**

#### 1. **MCP Server JWT Validation**
- ✅ MCP server correctly validates JWT tokens using `verify_jwt_token()`
- ✅ Validates signature, expiration, issuer, and required claims
- ✅ Extracts user_id from `sub` claim
- ✅ Extracts scopes from token payload
- ✅ Proper error handling and logging

**Location:** `mcp-server/auth.py`, `mcp-server/main.py`

#### 2. **User Identity Extraction in Orchestrator**
- ✅ Orchestrator correctly extracts user identity from LiveKit participant metadata
- ✅ Falls back to participant identity pattern if metadata unavailable
- ✅ Creates Redis session with user information
- ✅ Handles both web and mobile platforms

**Location:** `livekit-voice-agent/agent.py:526-588`

#### 3. **Token Flow Design (Conceptual)**
- ✅ Architecture document correctly specifies:
  - Pre-LiveKit authentication (Phase 1-2)
  - LiveKit connection with user metadata (Phase 3)
  - Orchestrator session initialization (Phase 4)
  - MCP tool call authentication (Phase 5)

**Location:** `docs/architecture.md:333-354`

---

## ❌ **Critical Gaps Identified**

### Gap 1: **Missing JWT Generation in Orchestrator**

**Issue:** The orchestrator does not generate JWT tokens for MCP calls.

**Current State:**
- Orchestrator extracts `user_id` from LiveKit participant metadata ✅
- Orchestrator stores session in Redis ✅
- **MISSING:** No JWT generation logic for MCP calls ❌
- **MISSING:** No MCP client integration ❌

**Expected Behavior (from architecture.md:333-354):**
```python
# Orchestrator generates short-lived JWT for MCP
jwt_payload = {
    "iss": "orchestrator",
    "sub": user_id,
    "scopes": ["transact"],  # Based on operation
    "session_id": room_name,
    "iat": now(),
    "exp": now() + timedelta(minutes=5),
    "jti": str(uuid4())
}
jwt_token = jwt.encode(jwt_payload, MCP_SECRET_KEY, algorithm="HS256")
```

**Impact:** 
- 🔴 **CRITICAL:** MCP server cannot authenticate requests
- 🔴 **CRITICAL:** Current implementation uses mock data instead of real MCP calls
- 🔴 **SECURITY:** No token-based authentication for banking operations

**Recommendation:**
1. Create `livekit-voice-agent/mcp_client.py` module
2. Implement JWT generation function using shared secret with MCP server
3. Implement MCP HTTP client that calls MCP server endpoints
4. Replace mock function tools with real MCP calls

---

### Gap 2: **MCP Server Token Parameter vs HTTP Header**

**Issue:** Architecture document shows HTTP Authorization header, but MCP protocol passes tokens as function parameters.

**Current Implementation:**
```python
@mcp.tool()
async def get_balance(
    jwt_token: str,  # Token passed as parameter
    account_type: Optional[str] = None
) -> List[dict]:
```

**Architecture Document Shows:**
```http
POST /mcp/payment
Authorization: Bearer <jwt>
```

**Analysis:**
- ✅ **MCP Protocol Design:** FastMCP uses function parameters for authentication, which is correct for MCP protocol
- ⚠️ **Architecture Document:** Shows HTTP-style headers, which is misleading
- ✅ **Current Implementation:** Correctly uses MCP protocol conventions

**Recommendation:**
- Update architecture document to reflect MCP protocol (function parameters)
- OR: If using HTTP transport, implement middleware to extract Authorization header
- **Decision Needed:** Which transport method are we using? (MCP protocol vs HTTP REST API)

---

### Gap 3: **Missing MCP Client Integration**

**Issue:** Orchestrator uses mock data instead of calling MCP server.

**Current State:**
- `agent.py` contains hardcoded mock accounts, transactions, loans
- Function tools (`check_account_balance`, `make_payment`, etc.) use mock data
- No HTTP client or MCP client to call MCP server

**Expected State:**
- Orchestrator should call MCP server tools via HTTP or MCP protocol
- Function tools should be thin wrappers that call MCP server
- All banking logic should be in MCP server

**Impact:**
- 🔴 **CRITICAL:** No real banking operations possible
- 🔴 **CRITICAL:** Architecture not implemented as designed

**Recommendation:**
1. Create `livekit-voice-agent/mcp_client.py`:
   ```python
   import httpx
   from jose import jwt
   from datetime import datetime, timedelta
   import uuid
   
   class MCPClient:
       def __init__(self, mcp_url: str, jwt_secret: str, jwt_issuer: str):
           self.mcp_url = mcp_url
           self.jwt_secret = jwt_secret
           self.jwt_issuer = jwt_issuer
       
       def _generate_jwt(self, user_id: str, scopes: list[str], session_id: str) -> str:
           payload = {
               "iss": self.jwt_issuer,
               "sub": user_id,
               "scopes": scopes,
               "session_id": session_id,
               "iat": datetime.utcnow(),
               "exp": datetime.utcnow() + timedelta(minutes=5),
               "jti": str(uuid.uuid4())
           }
           return jwt.encode(payload, self.jwt_secret, algorithm="HS256")
       
       async def get_balance(self, user_id: str, session_id: str, account_type: str = None):
           token = self._generate_jwt(user_id, ["read"], session_id)
           # Call MCP server via HTTP or MCP protocol
   ```

2. Replace mock function tools with MCP client calls
3. Remove hardcoded mock data from `agent.py`

---

### Gap 4: **Scope-Based Authorization Not Implemented**

**Issue:** MCP server checks for `read` scope, but orchestrator doesn't determine scopes based on operation type.

**Current State:**
- MCP server validates scopes ✅
- MCP server requires `read` scope for all operations ⚠️
- Orchestrator doesn't determine scopes based on operation ❌

**Expected Behavior:**
- Read operations: `["read"]`
- Transaction operations: `["transact"]`
- Configuration operations: `["configure"]`
- Orchestrator should determine scope based on which tool is being called

**Impact:**
- 🟡 **MEDIUM:** Authorization model not fully implemented
- 🟡 **MEDIUM:** All operations currently require `read` scope only

**Recommendation:**
1. Update MCP server scope validation:
   ```python
   def get_user_from_token(jwt_token: str, required_scope: str) -> User:
       payload = verify_jwt_token(jwt_token)
       scopes = payload.get("scopes", [])
       if required_scope not in scopes:
           raise ValueError(f"Missing required '{required_scope}' scope")
   ```

2. Update orchestrator to generate tokens with appropriate scopes:
   ```python
   # For read operations
   token = mcp_client._generate_jwt(user_id, ["read"], session_id)
   
   # For payment operations
   token = mcp_client._generate_jwt(user_id, ["transact"], session_id)
   ```

---

### Gap 5: **Missing Shared Secret Configuration**

**Issue:** Orchestrator and MCP server need shared JWT secret, but configuration is not aligned.

**Current State:**
- MCP server reads `MCP_JWT_SECRET_KEY` from environment ✅
- Orchestrator doesn't have JWT generation logic ❌
- No documented shared secret configuration ❌

**Impact:**
- 🔴 **CRITICAL:** Cannot generate valid tokens without shared secret
- 🔴 **SECURITY:** Secret must be securely shared between services

**Recommendation:**
1. Document required environment variables:
   ```bash
   # Orchestrator
   MCP_JWT_SECRET_KEY=<shared-secret>
   MCP_JWT_ISSUER=orchestrator
   MCP_SERVER_URL=http://localhost:8001/mcp
   
   # MCP Server
   MCP_JWT_SECRET_KEY=<same-shared-secret>
   MCP_JWT_ISSUER=orchestrator
   ```

2. Use secrets management (Kubernetes secrets, AWS Secrets Manager, etc.) in production
3. Ensure both services use same secret and issuer

---

## Token Flow Diagram (Current vs Expected)

### Current Implementation Flow

```
Client → Auth Server → JWT Access Token
  ↓
Client → Connection Details API → LiveKit Participant Token (with metadata)
  ↓
Client → LiveKit Connection
  ↓
Orchestrator → Extract user_id from metadata ✅
  ↓
Orchestrator → Create Redis session ✅
  ↓
Orchestrator → Use mock data ❌ (SHOULD CALL MCP SERVER)
  ↓
[NO MCP CALLS HAPPENING]
```

### Expected Architecture Flow

```
Client → Auth Server → JWT Access Token
  ↓
Client → Connection Details API → LiveKit Participant Token (with metadata)
  ↓
Client → LiveKit Connection
  ↓
Orchestrator → Extract user_id from metadata ✅
  ↓
Orchestrator → Create Redis session ✅
  ↓
Orchestrator → Generate JWT for MCP (iss=orchestrator, sub=user_id, scopes=[...]) ❌ MISSING
  ↓
Orchestrator → Call MCP Server with JWT ❌ MISSING
  ↓
MCP Server → Validate JWT ✅
  ↓
MCP Server → Execute banking operation ✅
  ↓
MCP Server → Return result ✅
  ↓
Orchestrator → Mask PII → Return to user ✅
```

---

## Recommendations Summary

### Priority 1: Critical (Must Fix Before Production)

1. **Implement JWT Generation in Orchestrator**
   - Create `mcp_client.py` module
   - Implement `_generate_jwt()` function
   - Use shared secret with MCP server

2. **Implement MCP Client Integration**
   - Replace mock data with real MCP calls
   - Implement HTTP client or MCP protocol client
   - Update all function tools to call MCP server

3. **Configure Shared Secrets**
   - Document environment variables
   - Ensure orchestrator and MCP server use same secret
   - Set up secrets management for production

### Priority 2: Important (Should Fix Soon)

4. **Implement Scope-Based Authorization**
   - Update MCP server to check operation-specific scopes
   - Update orchestrator to generate tokens with correct scopes
   - Test authorization boundaries

5. **Update Architecture Documentation**
   - Clarify MCP protocol vs HTTP transport
   - Document actual token flow (function parameters)
   - Update diagrams to reflect implementation

### Priority 3: Nice to Have

6. **Add Token Refresh Logic**
   - Implement token refresh for long-running sessions
   - Handle token expiration gracefully

7. **Add Comprehensive Logging**
   - Log all JWT generation events
   - Log all MCP calls with trace IDs
   - Audit trail for security compliance

---

## Security Considerations

### ✅ **Security Strengths**

1. **JWT Validation:** MCP server properly validates tokens
2. **Short-Lived Tokens:** Architecture specifies 5-minute expiration
3. **Scope Validation:** MCP server checks scopes
4. **PII Masking:** Orchestrator masks PII before LLM/TTS

### ⚠️ **Security Concerns**

1. **Missing Token Generation:** Cannot authenticate without implementation
2. **Shared Secret Management:** Need secure secret distribution
3. **Token Storage:** Ensure tokens not logged or exposed
4. **Scope Enforcement:** Need to verify scope checks work correctly

---

## Conclusion

The **MCP server implementation is architecturally sound** and correctly validates JWT tokens. However, there is a **critical gap** in the orchestrator: it does not generate JWT tokens or call the MCP server. The current implementation uses mock data, which means the architecture is not fully implemented.

**Key Findings:**
- ✅ MCP server: Correctly implemented
- ✅ Token validation: Correctly implemented
- ❌ Token generation: Missing in orchestrator
- ❌ MCP client: Missing in orchestrator
- ⚠️ Architecture doc: Minor discrepancies (HTTP headers vs MCP protocol)

**Next Steps:**
1. Implement JWT generation in orchestrator
2. Implement MCP client integration
3. Replace mock data with real MCP calls
4. Test end-to-end token flow
5. Update architecture documentation

---

**Status:** ⚠️ **ARCHITECTURE PARTIALLY IMPLEMENTED** - Critical gaps prevent production deployment

