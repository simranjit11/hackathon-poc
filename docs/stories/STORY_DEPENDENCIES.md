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

## Mock Bank APIs Stories (3.0-3.9)

### Epic 1: Database Schema and Foundation
**Story 3.0: Banking Database Schema**
- **Dependencies**: None (foundation story)
- **Blocks**: All other banking stories (3.1-3.9)
- **Can Start**: Immediately
- **Status**: Prerequisite for all banking API stories

### Epic 2: Account and Balance Read Operations
**Story 3.1: Account Details API**
- **Dependencies**: 3.0 (Database Schema)
- **Blocks**: 3.2, 3.5 (Payment Initiation needs accounts)
- **Can Start**: After 3.0
- **Parallel Development**: Can work in parallel with 3.3, 3.4

**Story 3.2: Account Balance API**
- **Dependencies**: 3.0 (Database Schema), 3.1 (Account Details - for pattern reference)
- **Blocks**: None
- **Can Start**: After 3.0 (can reference 3.1 pattern)
- **Parallel Development**: Can work in parallel with 3.1, 3.3, 3.4

### Epic 3: Loans and Transactions Read Operations
**Story 3.3: Loans API**
- **Dependencies**: 3.0 (Database Schema)
- **Blocks**: None
- **Can Start**: After 3.0
- **Parallel Development**: Can work in parallel with 3.1, 3.2, 3.4

**Story 3.4: Transaction History API**
- **Dependencies**: 3.0 (Database Schema)
- **Blocks**: 3.6 (Payment Confirmation creates transactions)
- **Can Start**: After 3.0
- **Parallel Development**: Can work in parallel with 3.1, 3.2, 3.3

### Epic 4: Payment and Transfer Operations
**Story 3.5: Payment Initiation API**
- **Dependencies**: 3.0 (Database Schema), 3.1 (Account Details - for account validation)
- **Blocks**: 3.6 (Payment Confirmation)
- **Can Start**: After 3.0 and 3.1
- **Status**: Critical path for payment functionality

**Story 3.6: Payment Confirmation API**
- **Dependencies**: 3.0 (Database Schema), 3.5 (Payment Initiation)
- **Blocks**: None
- **Can Start**: After 3.5
- **Status**: Completes payment flow

### Epic 5: Payment Reminders Management
**Story 3.7: Payment Reminders API**
- **Dependencies**: 3.0 (Database Schema)
- **Blocks**: None
- **Can Start**: After 3.0
- **Parallel Development**: Can work in parallel with all other stories

### Supporting Stories
**Story 3.9: Internal Banking APIs**
- **Dependencies**: 3.1 (Account Details), 3.4 (Transaction History)
- **Blocks**: None
- **Can Start**: After 3.1 and 3.4
- **Purpose**: Enables MCP server integration

---

## Mock Bank APIs Development Phases

### Phase 1: Foundation (Week 1)
**Sequential:**
1. **3.0 Database Schema** ← **START HERE** (blocks all others)

### Phase 2: Read Operations (Week 1-2)
**Parallel Development:**
1. **3.1 Account Details** (after 3.0) ← **Parallel**
2. **3.2 Account Balance** (after 3.0) ← **Parallel**
3. **3.3 Loans API** (after 3.0) ← **Parallel**
4. **3.4 Transaction History** (after 3.0) ← **Parallel**

### Phase 3: Payment Operations (Week 2)
**Sequential:**
1. **3.5 Payment Initiation** (after 3.0, 3.1)
2. **3.6 Payment Confirmation** (after 3.5)

### Phase 4: Payment Reminders (Week 2-3)
**Parallel Development:**
1. **3.7 Payment Reminders** (after 3.0) ← **Parallel**

### Phase 5: Integration (Week 3)
**Sequential:**
1. **3.9 Internal Banking APIs** (after 3.1, 3.4)

---
