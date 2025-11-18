# Story Dependencies and Parallel Development Guide

**Last Updated:** 2025-01-XX  
**Purpose:** Identify story dependencies and parallel development opportunities

---

## Dependency Graph

```
Journey 1 (Read-Only):
┌─────────────────────────────────────────────────────────────┐
│ 1.0 Auth Server (PREREQUISITE - Issues JWTs)                │
└─────────────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────┐
│ 1.1 Authentication (FOUNDATION - Required by ALL)          │
└─────────────────────────────────────────────────────────────┘
         │
         ├─────────────────┬─────────────────┐
         │                 │                 │
         ▼                 ▼                 ▼
┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│ 1.2 Audio/STT│  │ 1.5 MCP Tools │  │ (Independent)│
└──────────────┘  └──────────────┘  └──────────────┘
         │                 │
         │                 │
         │                 │
         ▼                 │
┌──────────────┐          │
│ 1.4 LLM      │◄─────────┘
│ (with memory)│
└──────────────┘
         │
         ├─────────────────┐
         │                 │
         ▼                 ▼
┌──────────────┐  ┌──────────────┐
│ 1.5 MCP Tools│  │ 1.6 TTS      │
└──────────────┘  └──────────────┘
         │                 │
         └────────┬────────┘
                  │
                  ▼
         ┌──────────────┐
         │ 1.7 Narration │
         └──────────────┘
                  │
                  ▼
         ┌──────────────┐
         │ 1.3 PII Mask │  ← LOWEST PRIORITY (LAST)
         │  (Presidio)  │
         └──────────────┘

Journey 2 (Transactional):
┌─────────────────────────────────────────────────────────────┐
│ Requires: 1.1, 1.4, 1.5 (as foundation)                    │
└─────────────────────────────────────────────────────────────┘
         │
         ▼
┌──────────────┐
│ 2.1 Payment  │
└──────────────┘
         │
         ▼
┌──────────────┐
│ 2.2 Elicitation│
└──────────────┘
         │
         ├─────────────────┬─────────────────┐
         │                 │                 │
         ▼                 ▼                 │
┌──────────────┐  ┌──────────────┐          │
│ 2.3 UI Web   │  │ 2.4 UI Mobile│          │
└──────────────┘  └──────────────┘          │
         │                 │                 │
         └────────┬─────────┴─────────────────┘
                  │
                  ▼
         ┌──────────────┐
         │ 2.5 Response │
         └──────────────┘
                  │
                  ▼
         ┌──────────────┐
         │ 2.6 Receipt  │
         └──────────────┘
```

---

## Critical Path (Sequential Dependencies)

### Foundation Layer (Must Complete First)

**Story 1.0: Auth Server Implementation** ⚠️ **PREREQUISITE**
- **Dependencies:** None (foundation story)
- **Blocks:** 1.1 (needs auth server to issue tokens)
- **Can Start:** Immediately
- **Parallel Development:** None - must be done before 1.1

**Story 1.1: Pre-LiveKit Authentication** ⚠️ **CRITICAL PATH**
- **Dependencies:** 1.0 (needs auth server to issue tokens)
- **Blocks:** ALL other stories (they all need authentication/session)
- **Can Start:** After 1.0
- **Parallel Development:** None - this must be done first

---

### Journey 1: Read-Only Flow

**Story 1.2: Audio Capture and STT Integration** 🔥 **HIGH PRIORITY**
- **Dependencies:** 1.1 (needs session management)
- **Blocks:** 1.4 (needs transcripts for LLM)
- **Can Start:** After 1.1
- **Parallel Development:** Can work in parallel with 1.5 (MCP Tools)
- **Note:** Core voice pipeline - prioritize this

**Story 1.4: LLM Integration with Littellm Gateway** 🔥 **HIGH PRIORITY**
- **Dependencies:** 1.1 (session), 1.2 (transcripts)
- **Blocks:** 1.6, 1.7, 2.1 (need LLM for tool calls)
- **Can Start:** After 1.2 (can work WITHOUT PII masking initially)
- **Parallel Development:** Can work in parallel with 1.5 (MCP Tools)
- **Note:** Core LLM with memory - prioritize this. PII masking can be added later.

**Story 1.3: PII Masking with Presidio** ⚠️ **LOWEST PRIORITY - DO LAST**
- **Dependencies:** 1.2 (needs transcripts), 1.4 (can integrate after LLM is working)
- **Blocks:** None (can be added as enhancement after core flow works)
- **Can Start:** After 1.4, 1.6, 1.7 are complete (or even after Journey 2)
- **Parallel Development:** None - sequential dependency
- **Note:** Security enhancement - can be added after core functionality is working

**Story 1.5: MCP Read Tools**
- **Dependencies:** 1.1 (needs JWT generation)
- **Blocks:** 1.6, 1.7 (need data to format/narrate)
- **Can Start:** After 1.1 (can work in parallel with 1.2, 1.3, 1.4)
- **Parallel Development:** ✅ **CAN DEVELOP IN PARALLEL** with 1.2, 1.3, 1.4

**Story 1.6: TTS Response Generation**
- **Dependencies:** 1.4 (LLM responses), 1.5 (MCP results)
- **Blocks:** 1.7 (needs TTS for narration)
- **Can Start:** After 1.4 AND 1.5
- **Parallel Development:** None - needs both dependencies

**Story 1.7: Natural Language Narration**
- **Dependencies:** 1.6 (TTS), 1.5 (data to format)
- **Blocks:** None (completes Journey 1)
- **Can Start:** After 1.6
- **Parallel Development:** None - final story in Journey 1

---

### Journey 2: Transactional Payments Flow

**Story 2.1: Payment Request Processing**
- **Dependencies:** 1.1 (JWT), 1.4 (LLM for intent extraction), 1.5 (MCP client pattern)
- **Blocks:** 2.2 (needs payment tool to create elicitations)
- **Can Start:** After 1.1, 1.4, 1.5
- **Parallel Development:** Can start once foundation stories are done

**Story 2.2: Elicitation Creation and State Management**
- **Dependencies:** 2.1 (payment tool creates elicitations), 1.1 (Redis session)
- **Blocks:** 2.3, 2.4, 2.5 (all need elicitation system)
- **Can Start:** After 2.1
- **Parallel Development:** None - foundation for elicitation UI

**Story 2.3: Elicitation UI Rendering (Web)**
- **Dependencies:** 2.2 (elicitation schema)
- **Blocks:** 2.5 (needs UI to collect responses)
- **Can Start:** After 2.2
- **Parallel Development:** ✅ **CAN DEVELOP IN PARALLEL** with 2.4 (Mobile UI)

**Story 2.4: Elicitation UI Rendering (Mobile with Biometric)**
- **Dependencies:** 2.2 (elicitation schema)
- **Blocks:** 2.5 (needs UI to collect responses)
- **Can Start:** After 2.2
- **Parallel Development:** ✅ **CAN DEVELOP IN PARALLEL** with 2.3 (Web UI)

**Story 2.5: Elicitation Response Handling**
- **Dependencies:** 2.2 (state management), 2.3 OR 2.4 (UI to collect responses)
- **Blocks:** 2.6 (needs payment completion)
- **Can Start:** After 2.2 AND (2.3 OR 2.4)
- **Parallel Development:** None - needs at least one UI implementation

**Story 2.6: Payment Completion and Receipt Display**
- **Dependencies:** 2.5 (payment completion), 1.6 (TTS for confirmation)
- **Blocks:** None (completes Journey 2)
- **Can Start:** After 2.5
- **Parallel Development:** None - final story in Journey 2

---

## Parallel Development Opportunities

### Phase 1: Foundation (Sequential)
- **1.0 Auth Server** → Must complete first
- **1.1 Authentication** → After 1.0

### Phase 2: Core Infrastructure (Parallel Opportunities) 🔥 **HIGH PRIORITY**

**Team A (Voice Pipeline - Core Flow):**
- 1.2 Audio/STT → 1.4 LLM Integration (with memory) → 1.6 TTS → 1.7 Narration
- **Note:** PII masking (1.3) moved to Phase 5 - do last

**Team B (Data Pipeline):**
- 1.5 MCP Read Tools (can start after 1.1)

**Note:** Teams A and B can work in parallel after 1.1 is complete. Core STT→LLM→TTS flow is priority.

### Phase 3: Response Generation (Sequential) 🔥 **HIGH PRIORITY**
- 1.6 TTS (needs 1.4 AND 1.5)
- 1.7 Narration (needs 1.6)
- **Note:** Core response generation - prioritize completing this flow

### Phase 5: Security Enhancement (Lowest Priority) ⚠️ **DO LAST**
- 1.3 PII Masking with Presidio (can be added after all core flows work)
- **Note:** Security enhancement - can be integrated after core functionality is proven

### Phase 4: Transactional Flow (Sequential with Parallel UI)

**Sequential:**
- 2.1 Payment Processing (needs 1.1, 1.4, 1.5)
- 2.2 Elicitation State (needs 2.1)

**Parallel UI Development:**
- 2.3 Web UI (needs 2.2) ← **Can develop in parallel**
- 2.4 Mobile UI (needs 2.2) ← **Can develop in parallel**

**Sequential Completion:**
- 2.5 Response Handling (needs 2.2 AND at least one UI)
- 2.6 Receipt Display (needs 2.5)

---

## Independent Development Opportunities

### Can Develop Independently (After Foundation)

**Story 1.5: MCP Read Tools**
- ✅ Independent after 1.1
- Only needs JWT generation (from 1.1)
- Can be developed by separate team
- No dependencies on voice pipeline (1.2, 1.3, 1.4)

**Story 2.3: Elicitation UI Web**
- ✅ Independent after 2.2
- Can develop web UI separately from mobile
- Only needs elicitation schema (from 2.2)

**Story 2.4: Elicitation UI Mobile**
- ✅ Independent after 2.2
- Can develop mobile UI separately from web
- Only needs elicitation schema (from 2.2)
- Can work in parallel with 2.3

---

## Development Phases Summary

### Phase 1: Foundation (Week 1)
**Sequential - Must Complete:**
1. ✅ **1.0 Auth Server** (PREREQUISITE - issues JWTs)
2. ✅ **1.1 Authentication** (CRITICAL - blocks everything)

### Phase 2: Core Infrastructure (Week 2-3) 🔥 **HIGH PRIORITY**
**Parallel Teams:**

**Team A - Voice Pipeline (Core Flow):**
1. 1.2 Audio/STT (after 1.1)
2. 1.4 LLM Integration with memory (after 1.2) - **NO PII masking needed initially**
3. 1.6 TTS (after 1.4 AND 1.5)
4. 1.7 Narration (after 1.6)

**Team B - Data Pipeline:**
1. 1.5 MCP Read Tools (after 1.1, parallel with Team A)

### Phase 3: Response Generation (Week 4) 🔥 **HIGH PRIORITY**
**Sequential:**
1. 1.6 TTS (after 1.4 AND 1.5)
2. 1.7 Narration (after 1.6)
- **Note:** Core response generation completes the basic voice assistant flow

### Phase 5: Security Enhancement (Week 7+) ⚠️ **LOWEST PRIORITY - DO LAST**
**Optional Enhancement:**
1. 1.3 PII Masking with Presidio (after core flows are working)
- **Note:** Can be added as security enhancement after all core functionality is proven

### Phase 4: Transactional Flow (Week 5-6)
**Sequential Foundation:**
1. 2.1 Payment Processing (after 1.1, 1.4, 1.5)
2. 2.2 Elicitation State (after 2.1)

**Parallel UI Development:**
1. 2.3 Web UI (after 2.2) ← **Parallel**
2. 2.4 Mobile UI (after 2.2) ← **Parallel**

**Sequential Completion:**
1. 2.5 Response Handling (after 2.2 AND at least one UI)
2. 2.6 Receipt Display (after 2.5)

---

## Dependency Matrix

| Story | Depends On | Blocks | Can Parallel With |
|-------|-----------|--------|-------------------|
| **1.0** | None | 1.1 | None |
| **1.1** | 1.0 | ALL | None |
| **1.2** | 1.1 | 1.4 | 1.5 |
| **1.4** | 1.1, 1.2 | 1.6, 1.7, 2.1 | 1.5 (if 1.5 doesn't need LLM) |
| **1.3** | 1.2, 1.4 | None (optional enhancement) | None |
| **1.5** | 1.1 | 1.6, 1.7 | 1.2, 1.3, 1.4 |
| **1.6** | 1.4, 1.5 | 1.7 | None |
| **1.7** | 1.6 | None | None |
| **2.1** | 1.1, 1.4, 1.5 | 2.2 | None |
| **2.2** | 2.1, 1.1 | 2.3, 2.4, 2.5 | None |
| **2.3** | 2.2 | 2.5 | 2.4 |
| **2.4** | 2.2 | 2.5 | 2.3 |
| **2.5** | 2.2, (2.3 OR 2.4) | 2.6 | None |
| **2.6** | 2.5, 1.6 | None | None |

---

## Recommended Development Order

### Sprint 1: Foundation
1. **1.0 Auth Server** (PREREQUISITE - do first)
2. **1.1 Authentication** (CRITICAL - after 1.0)

### Sprint 2: Core Infrastructure (Parallel) 🔥 **HIGH PRIORITY**
**Team A (Voice Pipeline - Core Flow):**
- 1.2 Audio/STT
- 1.4 LLM Integration with memory
- 1.6 TTS Response
- 1.7 Natural Language Narration

**Team B (Data Pipeline):**
- 1.5 MCP Read Tools

**Note:** PII masking (1.3) moved to Sprint 7+ as optional security enhancement

### Sprint 3: Response Generation 🔥 **HIGH PRIORITY**
- 1.6 TTS Response (if not completed in Sprint 2)
- 1.7 Natural Language Narration (if not completed in Sprint 2)
- **Note:** Core response generation completes basic voice assistant flow

### Sprint 4: Transactional Foundation
- 2.1 Payment Processing
- 2.2 Elicitation State Management

### Sprint 5: Elicitation UI (Parallel)
**Team A:**
- 2.3 Web UI

**Team B:**
- 2.4 Mobile UI

### Sprint 6: Completion
- 2.5 Elicitation Response Handling
- 2.6 Payment Completion

### Sprint 7+: Security Enhancement (Optional) ⚠️ **LOWEST PRIORITY**
- 1.3 PII Masking with Presidio
- **Note:** Can be added after all core flows are working and proven

---

## Key Insights

### Critical Path Stories (Must Complete in Order) 🔥 **HIGH PRIORITY**
1. **1.0** → **1.1** → **1.2** → **1.4** → **1.5** → **1.6** → **1.7** (Journey 1 core voice pipeline)
   - **Note:** 1.3 PII Masking removed from critical path - can be added later
2. **1.0, 1.1, 1.4, 1.5** → **2.1** → **2.2** → **2.5** → **2.6** (Journey 2 transactional flow)
3. **1.3 PII Masking** → Optional enhancement after core flows work (lowest priority)

### Best Parallel Opportunities 🔥 **HIGH PRIORITY**
- **1.5 MCP Tools** can be developed in parallel with **1.2, 1.4** (after 1.1)
- **1.2 Audio/STT** → **1.4 LLM** → **1.6 TTS** → **1.7 Narration** (core flow - prioritize)
- **2.3 Web UI** and **2.4 Mobile UI** can be developed in parallel (after 2.2)
- **1.3 PII Masking** can be added later as optional enhancement (lowest priority)

### Bottleneck Stories 🔥 **HIGH PRIORITY**
- **1.0 Auth Server**: Blocks 1.1 - prioritize this first
- **1.1 Authentication**: Blocks everything - prioritize this second
- **1.2 Audio/STT**: Blocks 1.4 LLM - core voice pipeline
- **1.4 LLM Integration**: Blocks Journey 1 completion and Journey 2 start - **HIGH PRIORITY**
- **1.5 MCP Tools**: Blocks 1.6 TTS and Journey 2 - **HIGH PRIORITY**
- **2.2 Elicitation State**: Blocks all elicitation UI work
- **1.3 PII Masking**: Not a bottleneck - optional enhancement (lowest priority)

---

## Risk Mitigation

### High-Risk Dependencies 🔥 **HIGH PRIORITY**
1. **1.0 Auth Server** - If delayed, blocks 1.1 and entire project
2. **1.1 Authentication** - If delayed, blocks entire project
3. **1.2 Audio/STT** - Core voice pipeline, blocks 1.4 LLM
4. **1.4 LLM Integration** - Complex integration, blocks multiple stories - **HIGH PRIORITY**
5. **1.5 MCP Tools** - Blocks 1.6 TTS and Journey 2 - **HIGH PRIORITY**
6. **2.2 Elicitation State** - Complex state management, blocks UI work

### Mitigation Strategies
- Start 1.0 immediately and prioritize (auth server must be done first)
- Start 1.1 immediately after 1.0 completes
- **Prioritize core flow: 1.2 → 1.4 → 1.5 → 1.6 → 1.7** (core voice assistant)
- Begin 1.5 MCP Tools in parallel with 1.2/1.4 (doesn't need PII masking)
- Prototype elicitation schema early (can start UI mockups)
- **Defer 1.3 PII Masking** until core flows are working (lowest priority)

---

## Summary

**Total Stories:** 14  
**Foundation Stories:** 2 (1.0, 1.1)  
**Independent Stories:** 1 (1.5 after 1.1)  
**Parallel Opportunities:** 2 major (1.5 with voice pipeline, 2.3/2.4 UI)  
**Sequential Chains:** 3 (voice pipeline, data pipeline, transactional flow)

**Recommended Team Structure:**
- **Team 1:** Auth + Authentication + Core Voice Pipeline 🔥 **HIGH PRIORITY**
  - (1.0 → 1.1 → 1.2 → 1.4 → 1.6 → 1.7)
  - **Note:** PII masking (1.3) moved to Team 5 (lowest priority)
- **Team 2:** Data Pipeline 🔥 **HIGH PRIORITY**
  - (1.5 MCP Tools, can start after 1.1, parallel with Team 1)
- **Team 3:** Transactional Flow 🔥 **HIGH PRIORITY**
  - (2.1 → 2.2 → 2.5 → 2.6)
- **Team 4:** UI Development
  - (2.3 Web, 2.4 Mobile - parallel after 2.2)
- **Team 5:** Security Enhancement ⚠️ **LOWEST PRIORITY**
  - (1.3 PII Masking - can start after core flows are working)

