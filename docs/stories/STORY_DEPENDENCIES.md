# Story Dependencies and Parallel Development Guide

**Last Updated:** 2025-11-20  
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
    ┌──────────────┐      │
    │ 1.4 LLM      │◄─────┘
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
┌─────────────────────────────────────────────────────────────┐
│ 2.0 Beneficiaries (NEW PREREQUISITE)                       │
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

## Critical Path Updates

### Transactional Flow

**Story 2.0: Beneficiary Management** ⚠️ **NEW PREREQUISITE**
- **Dependencies**: 1.0 (Auth Server - for DB schema), 1.1 (Authentication - for internal API security)
- **Blocks**: 2.1 (Payment processing needs beneficiaries to resolve "Pay Bob")
- **Can Start**: Immediately after 1.1
- **Parallel Development**: Can work in parallel with 1.2, 1.4, 1.5

**Story 2.1: Payment Request Processing**
- **Dependencies**: 2.0 (Beneficiaries), 1.1 (JWT), 1.4 (LLM), 1.5 (MCP client)
- **Blocks**: 2.2
- **Status Update**: Now blocked by 2.0

---

## Development Phases Summary

### Phase 4: Transactional Flow (Week 5-6)
**Sequential Foundation:**
1. **2.0 Beneficiary Management** (After 1.1) <-- **START HERE**
2. 2.1 Payment Processing (after 2.0, 1.4, 1.5)
3. 2.2 Elicitation State (after 2.1)

**Parallel UI Development:**
1. 2.3 Web UI (after 2.2) ← **Parallel**
2. 2.4 Mobile UI (after 2.2) ← **Parallel**

**Sequential Completion:**
1. 2.5 Response Handling (after 2.2 AND at least one UI)
2. 2.6 Receipt Display (after 2.5)

---
