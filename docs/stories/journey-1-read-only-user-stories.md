# Journey 1: Read-Only (Balances, Transactions, Loans) - User Stories

## Overview
This document breaks down Journey 1: Read-Only inquiries into detailed user stories with acceptance criteria. Each story identifies the Primary Service responsible for implementation.

---

## Story 1: Capture Read-Only Inquiry via Voice Input

**As a** banking customer  
**I want to** ask questions about my account balances, transactions, or loans using voice commands  
**So that** I can get information hands-free

**Primary Service:** Client (Web/Mobile)

**Acceptance Criteria:**
- [ ] Client captures audio input from user microphone
- [ ] Audio stream is sent to LiveKit SFU in real-time
- [ ] Client displays visual indicator that audio is being captured (e.g., waveform animation)
- [ ] Client handles microphone permissions gracefully on both web and mobile platforms
- [ ] Client supports interruption handling (user can stop/cancel mid-speech)
- [ ] Audio quality meets minimum requirements for STT processing (16kHz, mono, PCM)
- [ ] Client provides visual feedback when inquiry is being processed

---

## Story 2: Transcribe Read-Only Inquiry Audio Stream

**As a** system component  
**I want to** convert audio speech to text in real-time  
**So that** the inquiry intent can be understood and processed

**Primary Service:** Orchestrator (with STT Provider integration)

**Acceptance Criteria:**
- [ ] Orchestrator receives audio packets from LiveKit
- [ ] Orchestrator streams audio to STT Provider (AssemblyAI/Deepgram)
- [ ] STT Provider returns partial transcript fragments as user speaks
- [ ] Orchestrator aggregates transcript fragments into complete utterances
- [ ] Transcript is stored in Redis session cache for conversation context
- [ ] STT errors are handled gracefully with fallback to text input option
- [ ] Transcript includes timestamps for observability tracking
- [ ] Partial transcripts are displayed to user in real-time (optional enhancement)

---

## Story 3: Mask PII in Read-Only Inquiry Transcripts

**As a** compliance system  
**I want to** mask personally identifiable information before processing  
**So that** sensitive data is protected throughout the conversation flow

**Primary Service:** Orchestrator (Inline Presidio)

**Acceptance Criteria:**
- [ ] Presidio runs inline within Orchestrator process before LLM calls
- [ ] PII entities (account numbers, SSNs, phone numbers, etc.) are detected and masked
- [ ] Masked transcript replaces original transcript in all downstream processing
- [ ] Original transcript is NOT logged or persisted (only masked version)
- [ ] Masking latency is optimized to meet real-time conversation requirements (<100ms)
- [ ] Masking accuracy is validated against representative banking transcripts
- [ ] Masked entities are replaced with consistent placeholders (e.g., `[ACCOUNT_NUMBER]`)

---

## Story 4: Process Read-Only Inquiry Intent with Context

**As a** system component  
**I want to** understand the user's inquiry and determine which read tool to call  
**So that** the correct account information can be retrieved

**Primary Service:** Orchestrator (with LLM integration via Littellm Gateway)

**Acceptance Criteria:**
- [ ] Orchestrator constructs prompt with masked transcript and conversation history
- [ ] Conversation history is retrieved from Redis session cache
- [ ] Prompt includes user context (account types, recent inquiries)
- [ ] LLM request is routed through Littellm Gateway inside Orchestrator
- [ ] LLM returns structured tool call plan identifying:
  - Inquiry type (balance, transactions, loans)
  - Account identifier (if specified)
  - Date range (if applicable)
  - Filter parameters (if applicable)
- [ ] Tool call parameters are validated against structured schema
- [ ] LLM responses are constrained to pre-registered read-only tool calls only
- [ ] Prompt injection attempts are detected and blocked
- [ ] Ambiguous inquiries trigger clarification requests

---

## Story 5: Retrieve Account Balance Information

**As a** banking customer  
**I want to** hear my account balances  
**So that** I know how much money I have available

**Primary Service:** MCP Read Tool (Balance Lookup)

**Acceptance Criteria:**
- [ ] MCP Balance Tool receives JWT-authenticated request from Orchestrator
- [ ] JWT includes read scope and user identity
- [ ] MCP validates JWT scope and session freshness
- [ ] Tool queries upstream banking API for account balances
- [ ] Results include all account types (checking, savings, credit, etc.)
- [ ] Results are masked before returning to Orchestrator
- [ ] Account numbers are partially masked (e.g., `****1234`)
- [ ] Balance data includes currency and account type
- [ ] Tool execution is logged with masked payloads for audit trail
- [ ] Results are cached per customer/session with appropriate TTL

---

## Story 6: Retrieve Transaction History

**As a** banking customer  
**I want to** see my recent transactions  
**So that** I can track my spending and account activity

**Primary Service:** MCP Read Tool (Transaction List)

**Acceptance Criteria:**
- [ ] MCP Transaction Tool receives JWT-authenticated request from Orchestrator
- [ ] JWT includes read scope and user identity
- [ ] MCP validates JWT scope and session freshness
- [ ] Tool accepts query parameters:
  - Account identifier (optional, defaults to all accounts)
  - Date range (optional, defaults to last 30 days)
  - Transaction type filter (optional)
  - Limit (optional, defaults to 20)
- [ ] Tool queries upstream banking API for transactions
- [ ] Results are sorted by date (most recent first)
- [ ] Results include: date, description, amount, type, account
- [ ] Results are masked before returning to Orchestrator
- [ ] Sensitive merchant information is masked appropriately
- [ ] Tool execution is logged with masked payloads for audit trail
- [ ] Results are cached per customer/session with shorter TTL (5 minutes)

---

## Story 7: Retrieve Loan Information

**As a** banking customer  
**I want to** hear details about my loans  
**So that** I can understand my loan status and payment schedule

**Primary Service:** MCP Read Tool (Loan Summary)

**Acceptance Criteria:**
- [ ] MCP Loan Tool receives JWT-authenticated request from Orchestrator
- [ ] JWT includes read scope and user identity
- [ ] MCP validates JWT scope and session freshness
- [ ] Tool queries upstream banking API for loan information
- [ ] Results include:
  - Loan type and account number (masked)
  - Current balance
  - Interest rate
  - Monthly payment amount
  - Next payment date
  - Remaining term
- [ ] Results are masked before returning to Orchestrator
- [ ] Loan account numbers are partially masked
- [ ] Tool execution is logged with masked payloads for audit trail
- [ ] Results are cached per customer/session with appropriate TTL

---

## Story 8: Route Read Tool Calls Based on Inquiry Type

**As a** system component  
**I want to** call the appropriate MCP read tool based on inquiry intent  
**So that** users get accurate information efficiently

**Primary Service:** Orchestrator

**Acceptance Criteria:**
- [ ] Orchestrator analyzes LLM tool call to determine inquiry type
- [ ] Orchestrator routes to appropriate MCP tool:
  - Balance inquiries → Balance Lookup Tool
  - Transaction inquiries → Transaction List Tool
  - Loan inquiries → Loan Summary Tool
- [ ] Orchestrator extracts and validates tool parameters from LLM response
- [ ] Orchestrator generates short-lived JWT with read scope
- [ ] Orchestrator handles tool call errors gracefully
- [ ] Orchestrator supports multiple tool calls for complex inquiries (e.g., "show me balances and recent transactions")
- [ ] Tool call routing is logged for observability

---

## Story 9: Generate Voice Response for Read-Only Data

**As a** banking customer  
**I want to** hear a natural language summary of my account information  
**So that** I understand my financial status without reading

**Primary Service:** Orchestrator (with TTS Engine integration)

**Acceptance Criteria:**
- [ ] Orchestrator receives masked JSON results from MCP Read Tool
- [ ] Orchestrator formats data into natural language narration
- [ ] Narration includes:
  - Summary of what was requested
  - Key data points (balances, transaction counts, loan details)
  - Contextual information (e.g., "Your checking account balance is...")
- [ ] Orchestrator sends narration request to TTS Engine (Cartesia/ElevenLabs)
- [ ] TTS Engine converts text to speech audio stream
- [ ] Audio stream is sent to LiveKit for delivery to Client
- [ ] Narration is concise but complete (avoids information overload)
- [ ] TTS errors are handled gracefully with fallback to text response
- [ ] Audio quality meets minimum requirements for clear playback

---

## Story 10: Display Data Card for Read-Only Information

**As a** banking customer  
**I want to** see a visual card with my account information  
**So that** I can review details at a glance

**Primary Service:** Client (Web/Mobile)

**Acceptance Criteria:**
- [ ] Client receives masked JSON results via LiveKit data channel
- [ ] Client renders appropriate data card based on inquiry type:
  - **Balance Card**: Shows account list with balances, account types, currency
  - **Transaction Card**: Shows transaction list with date, description, amount, type
  - **Loan Card**: Shows loan details with balance, payment, interest rate, next due date
- [ ] Data cards follow design system and are accessible
- [ ] Account numbers are partially masked in display (e.g., `****1234`)
- [ ] Sensitive information is masked appropriately per policy
- [ ] Cards are scrollable for long lists (transactions)
- [ ] Cards include visual indicators (icons, colors) for account types and transaction types
- [ ] Mobile and web implementations share consistent UI schema
- [ ] Cards are displayed simultaneously with audio narration

---

## Story 11: Handle Multiple Account Inquiries

**As a** banking customer  
**I want to** ask about multiple accounts or types of information in one query  
**So that** I can get comprehensive information efficiently

**Primary Service:** Orchestrator

**Acceptance Criteria:**
- [ ] Orchestrator recognizes when inquiry requests multiple data types
- [ ] Orchestrator makes parallel or sequential MCP tool calls as needed
- [ ] Orchestrator aggregates results from multiple tools
- [ ] Orchestrator formats combined response for TTS narration
- [ ] Client receives aggregated data and renders multiple cards or combined card
- [ ] Response maintains context and clarity (e.g., "You have 3 accounts. Your checking account balance is...")
- [ ] All tool calls are logged with trace IDs for observability

---

## Story 12: Cache Read-Only Results Appropriately

**As a** system component  
**I want to** cache read-only results per customer/session  
**So that** repeated inquiries are faster and reduce load on upstream systems

**Primary Service:** Orchestrator (with Redis caching)

**Acceptance Criteria:**
- [ ] Balance results are cached per customer/session with TTL (e.g., 5 minutes)
- [ ] Transaction results are cached with shorter TTL (e.g., 2 minutes)
- [ ] Loan results are cached with TTL (e.g., 10 minutes)
- [ ] Cache keys include customer ID, session ID, and query parameters
- [ ] Cache invalidation occurs on session timeout
- [ ] Cache hits are logged for observability
- [ ] Cache does not store raw sensitive data (only masked results)
- [ ] Cache respects data freshness requirements (balances more stale-tolerant than transactions)

---

## Story 13: Persist Read-Only Inquiry Audit Trail

**As a** compliance system  
**I want to** log all read-only inquiries with masked data  
**So that** we maintain an audit trail for regulatory compliance

**Primary Service:** Orchestrator

**Acceptance Criteria:**
- [ ] All read-only inquiries are logged to Postgres audit ledger
- [ ] Logs include masked transcripts, tool calls, and results
- [ ] Raw sensitive data is NOT persisted (only masked versions)
- [ ] Audit logs include trace IDs linking full inquiry flow
- [ ] Logs include timestamps, user ID, session ID, inquiry type
- [ ] Logs are retained according to compliance retention policies
- [ ] Logs are queryable for compliance reporting
- [ ] Conversation state and masked transcripts persist in Redis/Postgres
- [ ] Observability spans capture inquiry flow (`stt_chunk`, `presidio_mask`, `llm_request`, `tool_response`, `tts_stream`)

---

## Story 14: Handle Read-Only Inquiry Errors Gracefully

**As a** banking customer  
**I want to** receive clear error messages when inquiries fail  
**So that** I understand what went wrong and can retry if appropriate

**Primary Service:** Orchestrator (with Client integration)

**Acceptance Criteria:**
- [ ] Orchestrator detects errors from STT, LLM, MCP tools, or TTS
- [ ] Error reasons are categorized:
  - STT failure → fallback to text input option
  - LLM failure → retry with simplified prompt
  - MCP tool failure → user-friendly error message
  - TTS failure → fallback to text response
- [ ] User-friendly error messages are generated for each failure type
- [ ] Error is communicated via both TTS (if available) and UI
- [ ] Client displays error message clearly with actionable next steps
- [ ] Failed inquiries are logged for audit (with masked data)
- [ ] User can retry inquiry after addressing the error
- [ ] Critical failures escalate to human agent option

---

## Story 15: Support Conversation Context in Read-Only Inquiries

**As a** banking customer  
**I want to** ask follow-up questions that reference previous inquiries  
**So that** I can have natural conversations about my accounts

**Primary Service:** Orchestrator (with Redis session management)

**Acceptance Criteria:**
- [ ] Orchestrator maintains conversation context in Redis session cache
- [ ] Context includes recent inquiries and responses
- [ ] LLM prompt includes conversation history for context understanding
- [ ] Follow-up questions like "show me more" or "what about my savings account" are understood
- [ ] Context is used to resolve ambiguous references (e.g., "that account" refers to previously mentioned account)
- [ ] Context expires with session timeout
- [ ] Context size is limited to prevent prompt bloat (e.g., last 10 exchanges)
- [ ] Context includes masked transcripts only (no raw PII)

---

## Story 16: Monitor Read-Only Inquiry Metrics

**As a** operations team  
**I want to** track read-only inquiry metrics  
**So that** we can monitor system health and user behavior patterns

**Primary Service:** Orchestrator (with Observability integration)

**Acceptance Criteria:**
- [ ] Inquiry success ratio is tracked and exposed via Prometheus metrics
- [ ] Inquiry latency (end-to-end) is tracked with percentiles
- [ ] Inquiry types are categorized and counted (balance, transactions, loans)
- [ ] Cache hit ratio is measured and reported
- [ ] Error rates by component (STT, LLM, MCP, TTS) are tracked
- [ ] Metrics are surfaced to Grafana dashboards
- [ ] Alert rules trigger on anomalous patterns (high error rate, latency spike)
- [ ] Metrics include service-level breakdowns (STT, LLM, MCP, TTS latencies)
- [ ] All metrics exclude PII and use masked identifiers
- [ ] Observability spans are captured via OpenTelemetry

---

## Cross-Story Dependencies

- Stories 1-4 must be completed before Story 5-8 (data retrieval)
- Stories 5-8 (MCP tools) can be developed in parallel
- Stories 9-10 form the response flow and depend on data retrieval stories
- Stories 11-16 are enhancements and cross-cutting concerns

---

## Technical Notes

- All stories must ensure PII masking before logging/persistence
- Trace IDs must link all components in the inquiry flow for observability
- Mobile and web implementations must share data card schema for consistency
- Error handling must be graceful with fallback options
- All read operations require JWT authentication with read scope
- Caching strategy balances freshness with performance
- Conversation context enables natural follow-up questions

