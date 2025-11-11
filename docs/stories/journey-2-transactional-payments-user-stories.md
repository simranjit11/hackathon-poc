# Journey 2: Transactional Payments & Transfers - User Stories

## Overview
This document breaks down Journey 2: Transactional Payments & Transfers into detailed user stories with acceptance criteria. Each story identifies the Primary Service responsible for implementation.

---

## Story 1: Capture Payment/Transfer Request via Voice Input

**As a** banking customer  
**I want to** initiate a payment or transfer request using voice commands  
**So that** I can complete transactions hands-free

**Primary Service:** Client (Web/Mobile)

**Acceptance Criteria:**
- [ ] Client captures audio input from user microphone
- [ ] Audio stream is sent to LiveKit SFU in real-time
- [ ] Client displays visual indicator that audio is being captured (e.g., waveform animation)
- [ ] Client handles microphone permissions gracefully on both web and mobile platforms
- [ ] Client supports interruption handling (user can stop/cancel mid-speech)
- [ ] Audio quality meets minimum requirements for STT processing (16kHz, mono, PCM)

---

## Story 2: Transcribe Payment Request Audio Stream

**As a** system component  
**I want to** convert audio speech to text in real-time  
**So that** the payment intent can be processed

**Primary Service:** Orchestrator (with STT Provider integration)

**Acceptance Criteria:**
- [ ] Orchestrator receives audio packets from LiveKit
- [ ] Orchestrator streams audio to STT Provider (AssemblyAI/Deepgram)
- [ ] STT Provider returns partial transcript fragments as user speaks
- [ ] Orchestrator aggregates transcript fragments into complete utterances
- [ ] Transcript is stored in Redis session cache for conversation context
- [ ] STT errors are handled gracefully with fallback to text input option
- [ ] Transcript includes timestamps for observability tracking

---

## Story 3: Mask PII in Payment Request Transcripts

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

## Story 4: Process Payment Intent with Policy Context

**As a** system component  
**I want to** analyze the payment request with user policy state  
**So that** appropriate controls and validations can be applied

**Primary Service:** Orchestrator (with LLM integration via Littellm Gateway)

**Acceptance Criteria:**
- [ ] Orchestrator constructs prompt with masked transcript and policy state (auth status, limits)
- [ ] Prompt includes conversation history from Redis session cache
- [ ] LLM request is routed through Littellm Gateway inside Orchestrator
- [ ] LLM returns structured tool call plan with extracted parameters (amount, payee, account)
- [ ] Tool call parameters are validated against structured schema
- [ ] Policy checks are applied (e.g., transaction limits, account status)
- [ ] LLM responses are constrained to pre-registered tool calls only
- [ ] Prompt injection attempts are detected and blocked

---

## Story 5: Initiate Payment Request via MCP Tool

**As a** system component  
**I want to** invoke the payment tool with authenticated request  
**So that** the payment can be processed securely

**Primary Service:** Orchestrator (calling MCP Payment Tool)

**Acceptance Criteria:**
- [ ] Orchestrator generates short-lived JWT with appropriate scopes (transact)
- [ ] JWT includes user role and session freshness validation
- [ ] Payment request includes extracted parameters (amount, payee, from_account, to_account)
- [ ] Request includes risk attributes (transaction type, amount, payee risk score)
- [ ] MCP Payment Tool receives JWT-authenticated request
- [ ] MCP validates JWT scope and session freshness
- [ ] Tool execution is sandboxed to pre-registered endpoints only
- [ ] Request is logged with masked payloads for audit trail

---

## Story 6: Handle Payment Elicitation Requirement

**As a** system component  
**I want to** request additional user confirmation when required  
**So that** security controls (MFA, OTP) can be enforced

**Primary Service:** MCP Payment Tool

**Acceptance Criteria:**
- [ ] MCP Payment Tool determines if elicitation is required based on policy (amount, payee, risk)
- [ ] MCP returns `create_elicitation` response with structured schema
- [ ] Elicitation schema defines required fields (OTP, confirmation, supervisor approval)
- [ ] Elicitation includes validation rules and user-facing prompts
- [ ] Elicitation state is stored in Redis with expiration timeout
- [ ] Elicitation is linked to original payment request via trace ID
- [ ] Multiple elicitation types are supported (OTP, biometric, supervisor approval)

---

## Story 7: Render Elicitation Prompt to User

**As a** banking customer  
**I want to** see clear prompts for required confirmations  
**So that** I can complete the payment authorization

**Primary Service:** Client (Web/Mobile)

**Acceptance Criteria:**
- [ ] Client receives elicitation schema via LiveKit data channel
- [ ] Client renders appropriate UI based on elicitation type:
  - OTP: Input field for code entry
  - Confirmation: Clear payment details with confirm/cancel buttons
  - Biometric: Native biometric prompt (mobile only)
- [ ] Payment details are displayed clearly (amount, payee, account)
- [ ] UI follows shared JSON schema for elicitation fields
- [ ] Client validates user input before submission
- [ ] Client shows loading state while processing elicitation response
- [ ] Client handles elicitation expiration gracefully with user notification

---

## Story 8: Capture User Confirmation/OTP Input

**As a** banking customer  
**I want to** provide my confirmation or OTP code  
**So that** the payment can be authorized

**Primary Service:** Client (Web/Mobile)

**Acceptance Criteria:**
- [ ] Client captures user input (OTP code, confirmation button, biometric)
- [ ] Input is validated client-side before submission
- [ ] Client sends elicitation resolution payload to Orchestrator via LiveKit data channel
- [ ] Payload includes elicitation ID and user-provided values
- [ ] Mobile client applies biometric re-authentication before showing sensitive prompts
- [ ] Client handles input errors gracefully (invalid OTP, expired session)
- [ ] Client provides clear error messages for failed validations

---

## Story 9: Resume Payment Tool with User Confirmation

**As a** system component  
**I want to** complete the payment after receiving user confirmation  
**So that** the transaction can be finalized

**Primary Service:** Orchestrator (resuming MCP Payment Tool)

**Acceptance Criteria:**
- [ ] Orchestrator receives elicitation resolution payload from Client
- [ ] Orchestrator validates elicitation ID and retrieves suspended tool state from Redis
- [ ] Orchestrator verifies elicitation has not expired
- [ ] Orchestrator calls MCP Payment Tool with resume request including user input
- [ ] MCP validates user input (OTP, confirmation, etc.)
- [ ] MCP completes payment execution with upstream banking API
- [ ] Payment result is returned as masked JSON confirmation
- [ ] Trace IDs link elicitation lifecycle (`elicitation_created`, `elicitation_resolved`, `tool_resume`)

---

## Story 10: Generate Voice Confirmation Response

**As a** banking customer  
**I want to** hear a voice confirmation of my payment  
**So that** I know the transaction completed successfully

**Primary Service:** Orchestrator (with TTS Engine integration)

**Acceptance Criteria:**
- [ ] Orchestrator receives masked payment confirmation JSON from MCP
- [ ] Orchestrator formats confirmation message for voice narration
- [ ] Orchestrator sends narration request to TTS Engine (Cartesia/ElevenLabs)
- [ ] TTS Engine converts text to speech audio stream
- [ ] Audio stream is sent to LiveKit for delivery to Client
- [ ] Confirmation includes transaction ID, amount, payee (masked appropriately)
- [ ] TTS errors are handled gracefully with fallback to text response
- [ ] Audio quality meets minimum requirements for clear playback

---

## Story 11: Display Payment Receipt in UI

**As a** banking customer  
**I want to** see a visual receipt of my completed payment  
**So that** I have a record of the transaction

**Primary Service:** Client (Web/Mobile)

**Acceptance Criteria:**
- [ ] Client receives payment confirmation via LiveKit data channel
- [ ] Client renders receipt UI card with transaction details:
  - Transaction ID
  - Amount (formatted currency)
  - Payee name/account (masked appropriately)
  - Timestamp
  - Status (success/failed)
- [ ] Receipt UI matches design system and is accessible
- [ ] Receipt can be saved/shared (if policy allows)
- [ ] Receipt persists in transaction history
- [ ] Client displays receipt simultaneously with audio confirmation
- [ ] Mobile and web implementations share consistent UI schema

---

## Story 12: Handle Payment Failure Scenarios

**As a** banking customer  
**I want to** receive clear error messages when payments fail  
**So that** I understand what went wrong and can retry if appropriate

**Primary Service:** Orchestrator (with Client integration)

**Acceptance Criteria:**
- [ ] Orchestrator detects payment failures from MCP Tool
- [ ] Failure reasons are categorized (insufficient funds, invalid payee, fraud rule hit, etc.)
- [ ] User-friendly error messages are generated for each failure type
- [ ] Error is communicated via both TTS and UI
- [ ] Client displays error message clearly with actionable next steps
- [ ] Failed payment attempts are logged for audit (with masked data)
- [ ] User can retry payment after addressing the error
- [ ] Critical failures escalate to human agent option

---

## Story 13: Persist Payment Transaction Audit Trail

**As a** compliance system  
**I want to** log all payment transactions with masked data  
**So that** we maintain an audit trail for regulatory compliance

**Primary Service:** Orchestrator

**Acceptance Criteria:**
- [ ] All payment requests are logged to Postgres audit ledger
- [ ] Logs include masked transcripts, tool calls, and results
- [ ] Raw sensitive data is NOT persisted (only masked versions)
- [ ] Audit logs include trace IDs linking full transaction flow
- [ ] Logs include timestamps, user ID, session ID, and policy decisions
- [ ] Logs are retained according to compliance retention policies
- [ ] Logs are queryable for compliance reporting
- [ ] Observability spans capture payment flow (`stt_chunk`, `presidio_mask`, `llm_request`, `tool_response`, `elicitation_lifecycle`, `tts_stream`)

---

## Story 14: Recover Suspended Payment State After Restart

**As a** system component  
**I want to** resume payment transactions after orchestrator restart  
**So that** users don't lose progress on incomplete payments

**Primary Service:** Orchestrator (with Redis session recovery)

**Acceptance Criteria:**
- [ ] Payment tool suspension state is stored in Redis with expiration
- [ ] Outstanding elicitations are tracked in Redis with timestamps
- [ ] On orchestrator restart, session state is restored from Redis
- [ ] Stale elicitations (>15 minutes) expire with user notification
- [ ] User is prompted gracefully about suspended payment state
- [ ] User can choose to resume or cancel suspended payment
- [ ] Recovery process maintains trace ID continuity for observability

---

## Story 15: Enforce Multi-Factor Authentication Policies

**As a** security system  
**I want to** enforce MFA requirements based on payment risk  
**So that** transactions are properly secured

**Primary Service:** MCP Payment Tool (with Orchestrator policy integration)

**Acceptance Criteria:**
- [ ] MCP evaluates payment against risk policies (amount thresholds, payee risk, transaction type)
- [ ] MFA is enforced when policy requires it (OTP, device biometrics, supervisor approval)
- [ ] Policy decisions are logged for audit
- [ ] Mobile clients use native biometric authentication when available
- [ ] Web clients support OTP via SMS/email
- [ ] Supervisor approval workflow is supported for high-risk transactions
- [ ] Policy rules are configurable and auditable
- [ ] MFA bypass attempts are blocked and logged

---

## Story 16: Monitor Payment Transaction Metrics

**As a** operations team  
**I want to** track payment transaction metrics  
**So that** we can monitor system health and fraud patterns

**Primary Service:** Orchestrator (with Observability integration)

**Acceptance Criteria:**
- [ ] Payment success ratio is tracked and exposed via Prometheus metrics
- [ ] Average elicitation roundtrips per payment are measured
- [ ] Fraud rule hits are counted and categorized
- [ ] Payment latency (end-to-end) is tracked with percentiles
- [ ] Metrics are surfaced to Grafana dashboards
- [ ] Alert rules trigger on anomalous patterns (high failure rate, fraud spike)
- [ ] Metrics include service-level breakdowns (STT, LLM, MCP, TTS latencies)
- [ ] All metrics exclude PII and use masked identifiers

---

## Cross-Story Dependencies

- Stories 1-4 must be completed before Story 5 (payment initiation)
- Stories 6-8 must be completed before Story 9 (elicitation flow)
- Stories 9-11 form the completion flow and depend on all previous stories
- Stories 12-16 are cross-cutting concerns that enhance the core flow

---

## Technical Notes

- All stories must ensure PII masking before logging/persistence
- Trace IDs must link all components in the payment flow for observability
- Mobile and web implementations must share elicitation schema for consistency
- Error handling must be graceful with fallback options
- All sensitive operations require JWT authentication with appropriate scopes

