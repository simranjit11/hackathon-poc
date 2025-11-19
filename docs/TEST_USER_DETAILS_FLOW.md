# Test Flow: "Tell Me About Myself"

## Overview

This document describes the end-to-end test flow for user authentication and user details retrieval.

## Test Scenario

**User Action:** Login on frontend → Connect to voice agent → Ask: "Tell me about myself"

**Expected Flow:**
1. User logs in → Gets JWT access token
2. User connects to LiveKit → Agent extracts user_id from token metadata
3. User asks "Tell me about myself"
4. Agent calls `get_user_details` MCP tool
5. MCP server calls backend API to fetch user details
6. Agent narrates user details back to user

---

## Step-by-Step Flow

### Step 1: User Login

**Frontend:** `agent-starter-react/app/(auth)/login/page.tsx`

```typescript
// User enters credentials and logs in
POST /api/auth/login
Body: { email: "user@example.com", password: "password123" }

Response: {
  accessToken: "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  user: { id: "12345", email: "user@example.com", ... }
}
```

**Token stored in:** `localStorage.getItem('access_token')`

---

### Step 2: Get LiveKit Connection Details

**Frontend:** `agent-starter-react/hooks/useRoom.ts`

```typescript
POST /api/connection-details
Headers: { Authorization: Bearer <accessToken> }
Body: { room_config: { agents: [{ agent_name: "banking-assistant" }] } }

Response: {
  serverUrl: "wss://livekit.example.com",
  roomName: "voice_assistant_room_1234567890_abc123",
  participantToken: "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  participantName: "user"
}
```

**Participant Token Metadata:**
```json
{
  "user_id": "12345",
  "email": "user@example.com",
  "roles": ["customer"],
  "permissions": ["read", "transact", "configure"],
  "session_type": "voice_assistant"
}
```

---

### Step 3: Connect to LiveKit

**Frontend:** `agent-starter-react/hooks/useRoom.ts`

```typescript
room.connect(serverUrl, participantToken)
```

**LiveKit:** Establishes connection, agent receives room event

---

### Step 4: Agent Session Initialization

**Orchestrator:** `livekit-voice-agent/agent.py` (entrypoint function)

```python
# Extract user_id from participant metadata
metadata = json.loads(participant.metadata)
user_id = metadata.get("user_id")  # "12345"
email = metadata.get("email")       # "user@example.com"
roles = metadata.get("roles")      # ["customer"]
permissions = metadata.get("permissions")  # ["read", "transact", "configure"]

# Create Redis session
session_manager.create_session(
    user_id=user_id,
    email=email,
    roles=roles,
    permissions=permissions,
    room_name=room_name,
    platform="web"
)

# Set agent context
assistant.user_id = user_id
assistant.session_id = room_name

# Initialize Agno agent with MCP tools
mcp_tools = create_agno_mcp_tools(user_id, room_name)
agno_agent = AgnoAgent(tools=[mcp_tools], ...)
```

---

### Step 5: User Asks "Tell Me About Myself"

**User:** Speaks into microphone → "Tell me about myself"

**Flow:**
1. STT converts speech to text: "Tell me about myself"
2. Presidio masks any PII (none in this case)
3. Text sent to Agno agent

---

### Step 6: Agno Agent Calls MCP Tool

**Agno Agent:** `livekit-voice-agent/agno_tools.py`

```python
# Agno recognizes user wants their profile info
# Automatically calls get_user_details tool

# AuthenticatedMCPTools intercepts call
async def _call_tool("get_user_details", **kwargs):
    scopes = ["read"]  # From scope_map
    return await mcp_client._call_mcp_tool(
        "get_user_details",
        user_id="12345",
        session_id="voice_assistant_room_...",
        scopes=["read"]
    )
```

**MCP Client:** `livekit-voice-agent/mcp_client.py`

```python
# Generates JWT token for MCP server
jwt_token = _generate_jwt(
    user_id="12345",
    scopes=["read"],
    session_id="voice_assistant_room_..."
)

# Calls MCP server
POST http://localhost:8001/mcp/tools/get_user_details
Body: { jwt_token: "...", ... }
```

---

### Step 7: MCP Server Processes Request

**MCP Server:** `mcp-server/main.py`

```python
@mcp.tool()
async def get_user_details(jwt_token: str) -> dict:
    # Validate JWT and extract user_id
    user = get_user_from_token(jwt_token)  # user_id="12345"
    
    # Call backend API using API key
    backend_client = get_backend_client()
    user_details = await backend_client.get_user_details("12345")
    
    # Returns:
    return {
        "user_id": "12345",
        "email": "user@example.com",
        "name": "John Doe",
        "roles": ["customer"],
        "permissions": ["read", "transact", "configure"],
        "created_at": "2025-01-01T00:00:00.000Z",
        "last_login_at": "2025-01-15T10:30:00.000Z"
    }
```

**Backend API Call:** `mcp-server/backend_client.py`

```python
GET http://localhost:3000/api/internal/users/12345
Headers: { X-API-Key: <INTERNAL_API_KEY> }

Response: {
  "user": {
    "id": "12345",
    "email": "user@example.com",
    "name": "John Doe",
    "roles": ["customer"],
    "permissions": ["read", "transact", "configure"],
    ...
  }
}
```

---

### Step 8: Agent Narrates Response

**Agno Agent:** Receives user details from MCP tool

**Response Format:**
```python
{
    "user_id": "12345",
    "email": "user@example.com",
    "name": "John Doe",
    "roles": ["customer"],
    "permissions": ["read", "transact", "configure"]
}
```

**Agno generates natural language response:**
```
"Hello John Doe! Here's your profile information:
- Email: user@example.com
- Account Type: Customer
- Permissions: You can read account information, make transactions, and configure alerts.
Your account was created on January 1st, 2025, and you last logged in on January 15th, 2025."
```

**TTS:** Converts text to speech → Streams audio to LiveKit → User hears response

---

## Complete Authentication Chain

```
User Login
  ↓ JWT Access Token (user_id, email, roles, permissions)
Frontend → Connection Details API
  ↓ LiveKit Participant Token (includes metadata)
Frontend → LiveKit
  ↓ Participant Metadata Extraction
LiveKit → Orchestrator
  ↓ Redis Session Creation
Orchestrator → Agno Agent
  ↓ MCP Tool Call (get_user_details)
Agno → MCP Client
  ↓ JWT Token Generation (user_id, scopes)
MCP Client → MCP Server
  ↓ JWT Validation + User ID Extraction
MCP Server → Backend API Client
  ↓ API Key Authentication
Backend API Client → Backend API
  ↓ User Details Retrieval
Backend API → MCP Server
  ↓ User Details Response
MCP Server → MCP Client
  ↓ Tool Response
MCP Client → Agno Agent
  ↓ Natural Language Generation
Agno Agent → TTS
  ↓ Audio Stream
TTS → LiveKit → User
```

---

## Testing Checklist

### Prerequisites

- [ ] Backend API running (`npm run dev` in `agent-starter-react`)
- [ ] MCP Server running (`python main.py` in `mcp-server`)
- [ ] Orchestrator running (`python agent.py dev` in `livekit-voice-agent`)
- [ ] Redis running (for session management)
- [ ] PostgreSQL running (for user database)

### Environment Variables

**Backend API (.env.local):**
```bash
AUTH_SECRET_KEY=your-secret-key
INTERNAL_API_KEY=your-api-key-for-server-to-server
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/banking
```

**MCP Server (.env):**
```bash
MCP_JWT_SECRET_KEY=your-secret-key  # Must match orchestrator
MCP_JWT_ISSUER=orchestrator
INTERNAL_API_KEY=your-api-key-for-server-to-server  # Must match backend
BACKEND_API_URL=http://localhost:3000
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/banking
```

**Orchestrator (.env):**
```bash
MCP_JWT_SECRET_KEY=your-secret-key  # Must match MCP server
MCP_JWT_ISSUER=orchestrator
MCP_SERVER_URL=http://localhost:8001/mcp
REDIS_URL=redis://localhost:6379/0
```

### Test Steps

1. **Start Backend API:**
   ```bash
   cd agent-starter-react
   npm run dev
   ```

2. **Start MCP Server:**
   ```bash
   cd mcp-server
   python main.py
   ```

3. **Start Orchestrator:**
   ```bash
   cd livekit-voice-agent
   python agent.py dev
   ```

4. **Login on Frontend:**
   - Navigate to `http://localhost:3000/login`
   - Enter credentials: `user@example.com` / `password123`
   - Click "Login"
   - Verify token is stored

5. **Connect to Voice Agent:**
   - Navigate to assistant page
   - Click "Start Session"
   - Verify connection established

6. **Ask Agent:**
   - Speak: "Tell me about myself"
   - Wait for response

7. **Verify Response:**
   - Agent should narrate:
     - Your name
     - Your email
     - Your account type/roles
     - Your permissions
     - Account creation date
     - Last login date

---

## Expected Logs

### Backend API Logs
```
POST /api/auth/login - 200 OK
POST /api/connection-details - 200 OK
GET /api/internal/users/12345 - 200 OK (with X-API-Key header)
```

### MCP Server Logs
```
Get user details request received
Get user details request for user_id: 12345
User details retrieved for user_id: 12345, email: user@example.com
```

### Orchestrator Logs
```
Session initialized: session:voice_assistant_room_xxx:12345
User: 12345 (user@example.com), Roles: ['customer'], Permissions: ['read', 'transact', 'configure']
Set agent context: user_id=12345, session_id=voice_assistant_room_xxx
Initialized Agno agent with MCP server tools (auto-discovered) for user_id: 12345
```

---

## Troubleshooting

### Issue: "User not found" from backend API

**Check:**
1. User exists in database: `SELECT * FROM users WHERE id = '12345';`
2. API key matches: `INTERNAL_API_KEY` in both services
3. Backend API is running and accessible

### Issue: "Authentication failed" from MCP server

**Check:**
1. JWT secret key matches: `MCP_JWT_SECRET_KEY` in orchestrator and MCP server
2. JWT issuer matches: `MCP_JWT_ISSUER=orchestrator` in both
3. Token includes required scope: `["read"]`

### Issue: Agent doesn't call get_user_details tool

**Check:**
1. Agno agent initialized correctly
2. MCP tools discovered successfully
3. Tool name matches: `get_user_details`
4. Scope mapping includes: `"get_user_details": ["read"]`

### Issue: "Failed to fetch user details from backend API"

**Check:**
1. Backend API is running
2. `BACKEND_API_URL` is correct in MCP server
3. `INTERNAL_API_KEY` is set and matches
4. Network connectivity between MCP server and backend API

---

## Success Criteria

✅ User can login successfully  
✅ User can connect to voice agent  
✅ Agent extracts user_id from LiveKit metadata  
✅ Agent calls `get_user_details` MCP tool  
✅ MCP server authenticates with JWT  
✅ MCP server calls backend API with API key  
✅ Backend API returns user details  
✅ Agent narrates user details naturally  
✅ User hears their profile information  

---

## Next Steps After Success

1. Add more user profile fields (phone number, address, etc.)
2. Add user preferences endpoint
3. Add user account settings endpoint
4. Extend to other "about me" queries (account summary, recent activity, etc.)

