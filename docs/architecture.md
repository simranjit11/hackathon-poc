# Real-Time Banking Voice Agent - Complete Architecture Document

**Version:** 1.0  
**Last Updated:** 2025-01-XX  
**Status:** Architecture Specification

---

## Table of Contents

1. [System Overview](#system-overview)
2. [Architecture Principles](#architecture-principles)
3. [Component Architecture](#component-architecture)
4. [Authentication & Authorization Architecture](#authentication--authorization-architecture)
5. [Elicitation Architecture](#elicitation-architecture)
6. [Journey Flows](#journey-flows)
7. [Data Flow Architecture](#data-flow-architecture)
8. [Security Architecture](#security-architecture)
9. [Observability & Monitoring](#observability--monitoring)
10. [Error Handling & Recovery](#error-handling--recovery)
11. [Deployment Architecture](#deployment-architecture)
12. [API Specifications](#api-specifications)
13. [Data Models & Schemas](#data-models--schemas)

---

## System Overview

### Purpose

A real-time banking voice assistant enabling customers to interact with banking services via voice commands. Supports read-only inquiries, transactional payments, and alert configuration through natural language conversation.

### High-Level Architecture

```
┌─────────────┐         ┌──────────────┐         ┌─────────────┐
│   Client    │◄───────►│   LiveKit    │◄───────►│ Orchestrator│
│ (Web/Mobile)│         │     SFU      │         │   (Python)   │
└─────────────┘         └──────────────┘         └─────────────┘
                                                          │
                                                          ├──► STT Provider
                                                          ├──► LLM (via Littellm)
                                                          ├──► TTS Engine
                                                          ├──► MCP Server
                                                          ├──► Redis
                                                          └──► Postgres
```

### Core Components

| Component | Responsibility | Technology |
|-----------|---------------|------------|
| **LiveKit SFU** | Low-latency bi-directional media + data transport, session state, interruption handling via VAD | LiveKit Cloud/Self-hosted |
| **STT Provider** | Streams partial transcripts back to the orchestrator | AssemblyAI / Deepgram |
| **Littellm Gateway + Presidio** | Combined lightweight gateway inside orchestrator that masks PII before forwarding prompts to downstream LLMs | Inline in Orchestrator |
| **Secure AI Orchestrator** | Manages conversation memory, policy checks, inline Presidio masking, Littellm routing, MCP tool calls, Redis session cache, audit writes | Python (LiveKit Agents SDK) |
| **LLM** | Tool-constrained reasoning and response generation | OpenAI/Azure/Groq via LiveKit Agents |
| **MCP FastAPI Server** | Exposes hardened, JWT-authenticated banking tools; emits elicitation pauses when user validation is required | FastAPI (Python) |
| **Datastores** | Redis holds active session/context, Postgres stores masked transcripts, tool logs, audit ledger; optional encrypted media storage | Redis, Postgres, Object Storage |
| **TTS Engine** | Converts final JSON response to real-time speech streamed via LiveKit | Cartesia / ElevenLabs |
| **Client Apps** | Render live transcript, elicitation prompts, confirmations; capture user input to resolve elicitation | Next.js (Web), React Native (Mobile) |

---

## Architecture Principles

### Design Principles

1. **Security First**: PII masking at every layer, JWT-based authentication, MFA enforcement
2. **Low Latency**: Real-time voice interaction with <500ms response times
3. **Resilience**: Graceful degradation, session recovery, error handling
4. **Compliance**: Audit trails, data retention policies, regulatory compliance
5. **Scalability**: Stateless orchestrator, horizontal scaling, caching strategies
6. **Observability**: End-to-end tracing, comprehensive metrics, structured logging

### Architectural Decisions

- **Inline Presidio & Littellm**: Combined in orchestrator process to reduce microservice overhead while maintaining security
- **Pre-LiveKit Authentication**: User identity established before connection for security and audit
- **Sequential Elicitation**: One elicitation at a time to prevent user confusion
- **Shared Backend Schema**: All backends use identical elicitation schema; clients implement platform-specific rendering
- **Redis Session State**: Fast session recovery and state management
- **Postgres Audit Trail**: Persistent, queryable audit logs for compliance

---

## Component Architecture

### Orchestrator (Python)

**Responsibilities:**
- Conversation state management
- STT/LLM/TTS coordination
- PII masking via Presidio
- LLM routing via Littellm
- MCP tool invocation
- Elicitation state management
- Session persistence (Redis)
- Audit logging (Postgres)

**Key Modules:**
```
orchestrator/
├── session_manager.py      # Redis session management
├── stt_handler.py          # STT provider integration
├── llm_handler.py          # Littellm gateway + LLM calls
├── tts_handler.py          # TTS engine integration
├── mcp_client.py           # MCP tool invocation
├── elicitation_manager.py  # Elicitation state & routing
├── presidio_masker.py      # Inline PII masking
├── audit_logger.py         # Postgres audit writes
└── livekit_agent.py        # LiveKit agent entrypoint
```

### MCP Server (FastAPI)

**Responsibilities:**
- Banking tool execution
- JWT validation
- Elicitation creation
- Risk assessment
- Tool suspension/resumption

**Endpoints:**
```
POST /mcp/balance           # Get account balances
POST /mcp/transactions       # Get transaction history
POST /mcp/loans              # Get loan information
POST /mcp/payment            # Initiate payment
POST /mcp/payment/resume     # Resume payment with elicitation
POST /mcp/alerts             # Manage alerts
POST /mcp/elicitation/{id}/cancel  # Cancel elicitation
```

### Client Applications

**Web Client (Next.js)**
- LiveKit Web SDK integration
- Real-time transcript display
- Elicitation UI rendering
- Data card visualization
- Audio playback

**Mobile Client (React Native)**
- LiveKit RN SDK integration
- Biometric authentication
- Native UI components
- Platform-specific elicitation rendering

---

## Authentication & Authorization Architecture

### Authentication Flow

#### Phase 1: Initial Authentication

**Mobile:**
```
User → Login Screen → Credentials + Biometric Auth
  ↓
Auth Service validates → Returns Access Token + User Identity
```

**Web:**
```
User → Login Screen → Credentials + Optional 2FA
  ↓
Auth Service validates → Returns Access Token + User Identity
```

#### Phase 2: LiveKit Connection Setup

**API Endpoint:** `POST /api/connection-details`

**Request:**
```http
POST /api/connection-details
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "agent_name": "banking-assistant"
}
```

**Backend Processing:**
1. Validate access token (signature, expiration)
2. Extract user identity: `user_id`, `email`, `roles`, `permissions`
3. Generate LiveKit participant token with custom claims:
   ```json
   {
     "user_id": "12345",
     "email": "user@example.com",
     "roles": ["customer"],
     "permissions": ["read", "transact", "configure"],
     "session_type": "voice_assistant",
     "iat": 1234567890,
     "exp": 1234567890 + 3600
   }
   ```
4. Create unique room name: `voice_assistant_room_{timestamp}_{random}`
5. Return connection details

**Response:**
```json
{
  "serverUrl": "wss://livekit.example.com",
  "roomName": "voice_assistant_room_1234567890_abc123",
  "participantToken": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "participantName": "user"
}
```

#### Phase 3: LiveKit Connection

```typescript
// Client connects to LiveKit
const room = await connect(serverUrl, participantToken);

// Orchestrator receives connection event
// Extracts user_id from token claims
const userId = room.participants[user].metadata.user_id;
```

#### Phase 4: Orchestrator Session Initialization

```python
# Orchestrator creates Redis session
redis.setex(
    f"session:{room_name}:{user_id}",
    ttl=3600,  # 1 hour
    value=json.dumps({
        "user_id": user_id,
        "email": email,
        "roles": roles,
        "permissions": permissions,
        "session_start": timestamp,
        "room_name": room_name,
        "platform": "mobile" | "web"
    })
)
```

#### Phase 5: MCP Tool Call Authentication

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

# MCP validates JWT
# - Signature verification
# - Expiration check
# - Scope validation
# - Session freshness check
```

### Authorization Model

**Scopes:**
- `read`: Read-only operations (balances, transactions, loans)
- `transact`: Transactional operations (payments, transfers)
- `configure`: Configuration operations (alerts, reminders)

**Role-Based Access:**
- `customer`: Standard banking operations
- `supervisor`: Approval workflows
- `admin`: System administration

---

## Elicitation Architecture

### Elicitation Flow

```
┌─────────┐         ┌─────────────┐         ┌─────────────┐         ┌─────────┐
│   MCP   │────────▶│ Orchestrator│────────▶│   LiveKit   │────────▶│ Client  │
│  Tool   │         │             │         │ Data Channel│         │         │
└─────────┘         └─────────────┘         └─────────────┘         └─────────┘
     │                      │                       │                     │
     │                      │                       │                     │
     │                      │                       │                     ▼
     │                      │                       │              ┌─────────┐
     │                      │                       │              │  User   │
     │                      │                       │              │  Input  │
     │                      │                       │              └─────────┘
     │                      │                       │                     │
     │                      │◀──────────────────────┴─────────────────────│
     │                      │         (elicitation response)              │
     │                      │                                            │
     │◀─────────────────────│                                            │
     │  (resume tool)       │                                            │
     │                      │                                            │
     ▼                      │                                            │
┌─────────┐                │                                            │
│   MCP   │                │                                            │
│  Tool   │                │                                            │
│(resumed)│                │                                            │
└─────────┘                │                                            │
```

### Elicitation Lifecycle

**State Machine:**
```
CREATED → PENDING → PROCESSING → COMPLETED
   │         │           │            │
   │         │           │            │
   │         ▼           ▼            │
   │      EXPIRED    FAILED           │
   │         │           │            │
   └─────────┴───────────┴────────────┘
              (can be cancelled)
```

### Sequential Elicitation Queue

```python
# Redis structure for sequential elicitation queue
redis.lpush(f"elicitation_queue:{session_id}", elicitation_id_1)
redis.lpush(f"elicitation_queue:{session_id}", elicitation_id_2)

# Process one at a time
current_elicitation = redis.rpop(f"elicitation_queue:{session_id}")
# Only show this one to user
# After completion, process next one
```

### Elicitation State Management

**Redis Storage:**
```python
# Elicitation state
redis.hset(
    f"elicitation:{elicitation_id}",
    mapping={
        "tool_call_id": tool_call_id,
        "mcp_endpoint": mcp_endpoint,
        "user_id": user_id,
        "session_id": session_id,
        "status": "pending",
        "created_at": timestamp,
        "expires_at": expires_at,
        "schema": json.dumps(schema),
        "context": json.dumps(context)
    }
)
redis.expire(f"elicitation:{elicitation_id}", ttl=300)

# Tool suspension state
redis.hset(
    f"tool_suspension:{tool_call_id}",
    mapping={
        "mcp_endpoint": mcp_endpoint,
        "request_payload": json.dumps(request),
        "elicitation_id": elicitation_id,
        "user_id": user_id
    }
)
```

### Platform-Specific Elicitation Handling

**Mobile:**
- Biometric authentication required before OTP/confirmation
- Native biometric prompts (Face ID, Touch ID, Fingerprint)
- Platform-specific UI rendering

**Web:**
- OTP-based authentication only
- Web-optimized UI components
- No biometric requirement

---

## Journey Flows

### Journey 1: Read-Only Inquiries

**Flow:**
1. User speaks inquiry
2. Client → LiveKit: Audio stream
3. LiveKit → Orchestrator: Audio packets
4. Orchestrator → STT: Stream audio
5. STT → Orchestrator: Partial transcript
6. Orchestrator: Inline Presidio mask
7. Orchestrator → LLM: Prompt with masked context
8. LLM → Orchestrator: Tool call (read-only)
9. Orchestrator → MCP: JWT-auth request
10. MCP → Orchestrator: Masked JSON result
11. Orchestrator → TTS: Narration request
12. TTS → LiveKit: Audio stream
13. LiveKit → Client: Synthesized response
14. Client → User: Plays response + shows data card

**Supported Operations:**
- Account balance inquiries
- Transaction history
- Loan information
- Credit limit checks

### Journey 2: Transactional Payments & Transfers

**Flow:**
1. User requests transfer/payment
2. Client → LiveKit: Audio stream
3. LiveKit → Orchestrator: Audio packets
4. Orchestrator → STT: Stream audio
5. STT → Orchestrator: Transcript fragments
6. Orchestrator: Inline Presidio mask
7. Orchestrator → LLM: Prompt with policy state
8. LLM → Orchestrator: Tool call plan
9. Orchestrator → MCP: Initiate payment request with JWT + risk attrs
10. MCP → Orchestrator: `create_elicitation` (needs OTP/confirmation)
11. Orchestrator → Client: Elicitation schema via LiveKit data channel
12. Client → User: Render confirmation/OTP prompt
13. User → Client: Provide confirmation / OTP
14. Client → Orchestrator: Resolve elicitation payload
15. Orchestrator → MCP: Resume tool with user input
16. MCP → Orchestrator: Final confirmation JSON (masked)
17. Orchestrator → TTS: Narration request
18. TTS → LiveKit: Audio response
19. LiveKit → Client: Streamed confirmation
20. Client → User: Audio + receipt UI

**Security Controls:**
- MFA enforced by policy
- OTP via elicitation
- Device biometrics on mobile
- Optional supervisor approval

### Journey 3: Write Operations (Alerts, Reminders)

**Flow:**
1. User: "Set a low balance alert"
2. Client → LiveKit: Audio stream
3. LiveKit → Orchestrator: Audio packets
4. Orchestrator → STT: Transcribe
5. STT → Orchestrator: Transcript chunks
6. Orchestrator: Inline Presidio mask
7. Orchestrator → LLM: Prompt with existing alert state
8. LLM → Orchestrator: Tool call (alert type, threshold)
9. Orchestrator → MCP: Invoke alerts tool
10. MCP → Orchestrator: Needs missing fields → `create_elicitation`
11. Orchestrator → Client: Render structured form
12. Client → User: UI for alert type, threshold, due date
13. User → Client: Submit form
14. Client → Orchestrator: Resolve elicitation data
15. Orchestrator → MCP: Resume execution
16. MCP → Orchestrator: Confirmation payload (masked)
17. Orchestrator → TTS: Voice confirmation
18. TTS → LiveKit: Audio stream
19. LiveKit → Client: Playback + updated alerts list

---

## Data Flow Architecture

### Audio Flow

```
User Voice → Client Microphone
  ↓
Client Audio Capture (16kHz, mono, PCM)
  ↓
LiveKit SFU (WebRTC)
  ↓
Orchestrator Audio Handler
  ↓
STT Provider (Streaming)
  ↓
Partial Transcripts → Orchestrator
```

### Transcript Processing Flow

```
STT Transcript → Orchestrator
  ↓
Presidio Masking (Inline)
  ↓
Masked Transcript → Redis Session Cache
  ↓
Masked Transcript → LLM Prompt
  ↓
LLM Response → Orchestrator
  ↓
Tool Call Extraction
  ↓
MCP Tool Invocation
```

### Response Flow

```
MCP Result → Orchestrator
  ↓
Result Masking (if needed)
  ↓
Response Formatting
  ↓
TTS Engine
  ↓
Audio Stream → LiveKit
  ↓
Client Audio Playback
```

### Elicitation Data Flow

```
MCP Tool → Elicitation Required
  ↓
Elicitation Schema → Orchestrator
  ↓
Schema Storage (Redis)
  ↓
Schema → LiveKit Data Channel
  ↓
Client Receives Schema
  ↓
Client Renders UI
  ↓
User Input → Client
  ↓
Elicitation Response → LiveKit Data Channel
  ↓
Orchestrator Receives Response
  ↓
Response Validation
  ↓
MCP Tool Resume
```

---

## Security Architecture

### PII Masking Strategy

**Presidio Integration:**
- Runs inline within Orchestrator process
- Masks PII before LLM calls
- Masks PII before logging
- Masks PII before client transmission

**Masked Entities:**
- Account numbers
- Social Security Numbers
- Phone numbers
- Email addresses
- Credit card numbers
- Bank routing numbers

**Masking Format:**
- Account numbers: `****1234`
- SSNs: `***-**-1234`
- Phone: `(***) ***-1234`

### Authentication Security

**Token Management:**
- Short-lived JWTs (5-15 minutes)
- Refresh token rotation
- Token revocation support
- Session freshness validation

**Biometric Security:**
- Platform-native biometric APIs
- Biometric tokens for mobile
- No biometric data storage
- Secure token transmission

### Authorization Security

**Scope Enforcement:**
- MCP validates scopes before execution
- Orchestrator checks permissions
- Role-based access control
- Session-based authorization

**Tool Execution Security:**
- Sandboxed tool calls
- Pre-registered endpoints only
- Schema validation
- Prompt injection detection

### Data Security

**Encryption:**
- TLS for all communications
- Encrypted data at rest
- Encrypted media storage (optional)
- Certificate pinning (mobile)

**Audit & Compliance:**
- All operations logged (masked)
- Audit trail in Postgres
- Retention policies enforced
- Compliance reporting

---

## Observability & Monitoring

### Tracing

**OpenTelemetry Integration:**
- Trace IDs link all components
- Spans for each operation:
  - `stt_chunk`: STT processing
  - `presidio_mask`: PII masking
  - `llm_request`: LLM calls
  - `tool_response`: MCP tool results
  - `elicitation_lifecycle`: Elicitation flow
  - `tts_stream`: TTS generation

**Trace Propagation:**
```
User Request → Trace ID Generated
  ↓
Trace ID propagated through:
  - LiveKit headers
  - Orchestrator context
  - MCP requests
  - Redis keys
  - Postgres logs
```

### Metrics

**Key Metrics:**
- Request latency (p50, p95, p99)
- Error rates by component
- Elicitation success rate
- Payment success ratio
- Cache hit ratio
- Session duration
- Tool execution time

**Metrics Collection:**
- Prometheus exporters
- Grafana dashboards
- Alert rules for anomalies

### Logging

**Structured Logging:**
- JSON format
- PII removed
- Trace ID included
- Context preserved

**Log Destinations:**
- Centralized log store (Loki/ELK)
- Postgres audit logs
- Debug logs (development)

---

## Error Handling & Recovery

### Error Categories

**Transient Errors:**
- Network timeouts
- Service unavailability
- Rate limiting

**Permanent Errors:**
- Authentication failures
- Authorization denials
- Invalid input

**Recovery Strategies:**
- Retry with exponential backoff
- Fallback to alternative services
- Graceful degradation
- User notification

### Session Recovery

**Redis-Backed Recovery:**
- Session state persisted
- Tool suspension state stored
- Elicitation state preserved
- Automatic recovery on restart

**Recovery Flow:**
```
Orchestrator Restart
  ↓
Load Session from Redis
  ↓
Restore Tool Suspension State
  ↓
Check Elicitation Expiration
  ↓
Notify User of State
  ↓
Resume or Cancel Operations
```

### Graceful Degradation

**STT Failure:**
- Fallback to text input
- User can type instead

**TTS Failure:**
- Fallback to text response
- Display text in UI

**LLM Failure:**
- Retry with simplified prompt
- Escalate to human agent

**MCP Tool Failure:**
- Clear error message
- Retry option
- Escalation path

---

## Deployment Architecture

### Component Deployment

**Orchestrator:**
- Containerized (Docker)
- Kubernetes deployment
- Horizontal scaling
- Health checks

**MCP Server:**
- Containerized (Docker)
- Kubernetes deployment
- Load balancing
- Health checks

**Client Applications:**
- Web: Static hosting (Vercel/Netlify)
- Mobile: App stores (iOS/Android)

**Datastores:**
- Redis: Managed service or cluster
- Postgres: Managed service or cluster
- Object Storage: S3/GCS/Azure Blob

### Infrastructure

**LiveKit:**
- Cloud service or self-hosted
- Regional deployment
- CDN integration

**External Services:**
- STT Provider: API integration
- LLM Provider: API integration
- TTS Provider: API integration

### Scaling Strategy

**Horizontal Scaling:**
- Stateless orchestrator
- Multiple MCP instances
- Redis cluster
- Postgres read replicas

**Caching Strategy:**
- Redis session cache
- Result caching (balances, transactions)
- CDN for static assets

---

## API Specifications

### LiveKit Data Channel Messages

**Orchestrator → Client:**
```typescript
{
  "type": "elicitation",
  "payload": ElicitationRequest
}

{
  "type": "elicitation_status",
  "payload": ElicitationStatusUpdate
}

{
  "type": "data_card",
  "payload": DataCardResponse
}
```

**Client → Orchestrator:**
```typescript
{
  "type": "elicitation_response",
  "payload": ElicitationResponse
}

{
  "type": "elicitation_cancel",
  "elicitation_id": "..."
}
```

### MCP API Endpoints

**Payment Tool:**
```http
POST /mcp/payment
Authorization: Bearer <jwt>
Content-Type: application/json

{
  "amount": 500.00,
  "from_account": "checking",
  "to_account": "John Doe",
  "description": "Payment"
}
```

**Resume Payment:**
```http
POST /mcp/payment/resume
Authorization: Bearer <jwt>
Content-Type: application/json

{
  "elicitation_id": "uuid",
  "user_input": {
    "otp_code": "123456"
  }
}
```

---

## Data Models & Schemas

### Elicitation Request Schema

```typescript
interface ElicitationRequest {
  type: "elicitation";
  elicitation_id: string;
  tool_call_id: string;
  elicitation_type: "otp" | "confirmation" | "biometric" | "form" | "supervisor_approval";
  schema: {
    fields: Array<ElicitationField>;
    ui_hints?: {
      component?: "otp_input" | "confirmation_dialog" | "form" | "biometric_prompt";
      timeout_seconds?: number;
      retry_count?: number;
    };
  };
  context: {
    amount?: string;
    payee?: string;
    account?: string;
    transaction_type?: string;
  };
  metadata: {
    trace_id: string;
    created_at: string;
    expires_at: string;
    platform_requirements?: {
      mobile?: {
        requires_biometric: boolean;
        biometric_type?: "face_id" | "touch_id" | "fingerprint";
      };
      web?: {
        requires_biometric: boolean;
      };
    };
  };
}

interface ElicitationField {
  name: string;
  type: "string" | "number" | "boolean" | "date" | "select" | "otp";
  label: string;
  placeholder?: string;
  help_text?: string;
  validation?: {
    required?: boolean;
    pattern?: string;
    min?: number;
    max?: number;
    min_length?: number;
    max_length?: number;
    options?: Array<{
      value: string;
      label: string;
    }>;
  };
  mask_input?: boolean;
}
```

### Elicitation Response Schema

```typescript
interface ElicitationResponse {
  type: "elicitation_response";
  elicitation_id: string;
  data: Record<string, any>;
  metadata?: {
    biometric_token?: string;
    device_id?: string;
    platform?: "mobile" | "web";
    response_time_ms?: number;
  };
}
```

### Elicitation Status Update Schema

```typescript
interface ElicitationStatusUpdate {
  type: "elicitation_status";
  elicitation_id: string;
  status: "pending" | "processing" | "completed" | "expired" | "cancelled" | "failed";
  message?: string;
  error_code?: string;
  next_elicitation?: ElicitationRequest;
}
```

### Session State Schema

```typescript
interface SessionState {
  user_id: string;
  email: string;
  roles: string[];
  permissions: string[];
  session_start: string;
  room_name: string;
  platform: "mobile" | "web";
  conversation_context: ConversationContext;
  active_elicitations: string[];
}
```

---

## Conclusion

This architecture document provides a comprehensive specification for the Real-Time Banking Voice Agent system. It covers all aspects from authentication to deployment, ensuring security, scalability, and compliance throughout the system.

**Key Architectural Highlights:**
- Pre-LiveKit authentication with biometric support
- Sequential elicitation processing
- Shared backend schema with platform-specific client rendering
- Comprehensive PII masking at every layer
- End-to-end observability and tracing
- Resilient error handling and recovery

---

**Document Status:** Ready for Implementation  
**Next Steps:** Begin implementation following the user stories breakdowns

