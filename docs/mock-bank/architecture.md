# Mock Bank APIs Architecture Document

**Version:** 1.0  
**Last Updated:** 2025-01-XX  
**Status:** Architecture Specification  
**Related PRD:** [Mock Bank APIs PRD](./prd.md)

---

## Table of Contents

1. [System Overview](#system-overview)
2. [Architecture Integration](#architecture-integration)
3. [Component Architecture](#component-architecture)
4. [Data Models & Schema](#data-models--schema)
5. [API Design](#api-design)
6. [Authentication & Authorization](#authentication--authorization)
7. [Database Architecture](#database-architecture)
8. [Error Handling & Validation](#error-handling--validation)
9. [Source Tree Organization](#source-tree-organization)
10. [Testing Strategy](#testing-strategy)
11. [Deployment Integration](#deployment-integration)

---

## System Overview

### Purpose

The Mock Bank APIs provide comprehensive banking operation endpoints within the existing Next.js authentication server. These APIs enable:

- Account and balance inquiries
- Loan information retrieval
- Transaction history with filtering
- Payment and transfer processing
- Alert and notification management

### Integration with Existing System

The Mock Bank APIs are integrated as **Next.js API Routes** within the existing `agent-starter-react` application, leveraging:

- **Existing Authentication**: JWT token validation via `validateAccessToken` and `extractTokenFromHeader`
- **Existing CORS Utilities**: `corsResponse` and `corsPreflight` for cross-origin support
- **Existing Database**: PostgreSQL via Prisma ORM
- **Existing Patterns**: Follows established API route patterns from `/api/beneficiaries` and `/api/auth/*`

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Next.js Application                      │
│                  (agent-starter-react)                       │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌────────────────────────────────────────────────────┐   │
│  │         Existing API Routes                          │   │
│  │  /api/auth/*, /api/beneficiaries, /api/health        │   │
│  └────────────────────────────────────────────────────┘   │
│                                                              │
│  ┌────────────────────────────────────────────────────┐   │
│  │         NEW: Mock Bank API Routes                   │   │
│  │  /api/banking/accounts                              │   │
│  │  /api/banking/loans                                 │   │
│  │  /api/banking/transactions                          │   │
│  │  /api/banking/payments                              │   │
│  │  /api/banking/transfers                             │   │
│  │  /api/banking/alerts                                │   │
│  │  /api/banking/notifications                         │   │
│  └────────────────────────────────────────────────────┘   │
│                          │                                  │
│                          ▼                                  │
│  ┌────────────────────────────────────────────────────┐   │
│  │         Shared Libraries                             │   │
│  │  @/lib/auth (JWT validation)                        │   │
│  │  @/lib/cors (CORS utilities)                         │   │
│  │  @/lib/db/prisma (Database client)                  │   │
│  └────────────────────────────────────────────────────┘   │
│                          │                                  │
│                          ▼                                  │
│  ┌────────────────────────────────────────────────────┐   │
│  │         PostgreSQL Database                          │   │
│  │  - users (existing)                                  │   │
│  │  - beneficiaries (existing)                         │   │
│  │  - accounts (new)                                    │   │
│  │  - loans (new)                                       │   │
│  │  - transactions (new)                                │   │
│  │  - payment_alerts (new)                             │   │
│  │  - notification_preferences (new)                   │   │
│  └────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│              External Integrations                           │
│  - MCP Server (via /api/internal/* with API key)            │
│  - Voice Assistant (via authenticated JWT)                   │
└─────────────────────────────────────────────────────────────┘
```

---

## Architecture Integration

### Integration with Existing Architecture

The Mock Bank APIs integrate seamlessly with the existing Real-Time Banking Voice Agent architecture:

1. **Authentication Flow**: Uses the same JWT-based authentication established in the main architecture
2. **MCP Server Integration**: MCP server can call banking APIs via internal API key authentication (similar to `/api/internal/users/[id]`)
3. **Database Consistency**: Extends existing Prisma schema following established patterns
4. **Error Handling**: Follows existing error response patterns for consistency

### Compatibility Requirements

- **API Compatibility**: All endpoints follow RESTful conventions established in existing APIs
- **Database Schema Compatibility**: New tables use same naming conventions (snake_case, timestamps)
- **Authentication Compatibility**: All endpoints require JWT tokens, compatible with existing auth flow
- **Performance Impact**: Minimal - read operations <200ms, write operations <500ms

---

## Component Architecture

### API Route Handlers

All banking API routes follow the Next.js App Router pattern:

**Location**: `app/api/banking/{resource}/route.ts`

**Structure Pattern**:
```typescript
import { NextRequest, NextResponse } from 'next/server';
import { validateAccessToken, extractTokenFromHeader } from '@/lib/auth';
import { corsResponse, corsPreflight } from '@/lib/cors';
import { prisma } from '@/lib/db/prisma';

export async function GET(request: NextRequest) {
  // Handle CORS preflight
  if (request.method === 'OPTIONS') {
    return corsPreflight();
  }

  try {
    // Authentication
    const authHeader = request.headers.get('Authorization');
    const token = extractTokenFromHeader(authHeader);
    const user = await validateAccessToken(token);

    // Business logic
    // ...

    return corsResponse(data, 200);
  } catch (error) {
    // Error handling
    return corsResponse({ error: '...' }, statusCode);
  }
}

export async function OPTIONS() {
  return corsPreflight();
}
```

### Business Logic Layer

**Location**: `lib/banking/`

Organized by domain:
- `lib/banking/accounts.ts` - Account operations
- `lib/banking/loans.ts` - Loan operations
- `lib/banking/transactions.ts` - Transaction operations
- `lib/banking/payments.ts` - Unified payment processing (initiation and confirmation)
- `lib/banking/payment-otp.ts` - OTP generation and validation for payments
- `lib/banking/beneficiaries.ts` - Beneficiary resolution and lookup
- `lib/banking/alerts.ts` - Alert management
- `lib/banking/notifications.ts` - Notification preferences

**Purpose**: Separate business logic from route handlers for testability and reusability.

**Key Functions**:

```typescript
// lib/banking/beneficiaries.ts
export async function resolveBeneficiary(
  userId: string,
  identifier: { id?: string; nickname?: string }
): Promise<Beneficiary | null>

export async function getBeneficiaryPaymentDetails(
  beneficiaryId: string
): Promise<{ paymentAddress: string; paymentType: string }>

// lib/banking/payments.ts
export async function initiatePayment(
  userId: string,
  fromAccountId: string,
  options: {
    beneficiaryId?: string;
    beneficiaryNickname?: string;
    paymentAddress?: string;
    toAccount?: string; // For internal transfers
  },
  amount: number,
  description?: string
): Promise<{ transaction: Transaction; paymentSessionId: string; otpCode: string }>

export async function confirmPayment(
  userId: string,
  paymentSessionId: string,
  otpCode: string
): Promise<Transaction>

// lib/banking/payment-otp.ts
export async function generatePaymentOTP(
  transactionId: string
): Promise<{ sessionId: string; otpCode: string }>

export async function validatePaymentOTP(
  paymentSessionId: string,
  otpCode: string
): Promise<{ valid: boolean; transactionId?: string }>
```

### Validation Layer

**Location**: `lib/banking/validators.ts`

Centralized validation functions:
- Account ownership validation
- Balance sufficiency checks
- Transaction amount validation
- Beneficiary ownership validation (beneficiary belongs to user)
- Beneficiary resolution (by ID or nickname)
- OTP format validation (6-digit numeric)
- Payment session validation
- Transaction expiration validation
- Date range validation
- Pagination parameter validation
- UPI ID format validation
- Account number format validation

---

## Data Models & Schema

### Prisma Schema Extensions

New models added to `prisma/schema.prisma`:

```prisma
model Account {
  id            String   @id @default(uuid())
  userId        String   @map("user_id")
  accountNumber String   @unique @map("account_number")
  accountType   String   @map("account_type") // "checking" | "savings" | "credit_card"
  balance       Decimal  @db.Decimal(15, 2)
  creditLimit   Decimal? @map("credit_limit") @db.Decimal(15, 2) // For credit cards
  currency      String   @default("USD")
  status        String   @default("active") // "active" | "closed" | "frozen"
  createdAt     DateTime @default(now()) @map("created_at")
  updatedAt     DateTime @updatedAt @map("updated_at")

  user         User          @relation(fields: [userId], references: [id], onDelete: Cascade)
  transactions Transaction[]
  loans        Loan[]

  @@index([userId])
  @@index([accountType])
  @@index([status])
  @@map("accounts")
}

model Loan {
  id                String   @id @default(uuid())
  userId            String   @map("user_id")
  accountId         String?  @map("account_id") // Optional link to account
  loanType          String   @map("loan_type") // "mortgage" | "auto" | "personal"
  loanNumber        String   @unique @map("loan_number")
  outstandingBalance Decimal @map("outstanding_balance") @db.Decimal(15, 2)
  interestRate      Decimal  @map("interest_rate") @db.Decimal(5, 4) // e.g., 3.75% = 0.0375
  monthlyPayment    Decimal  @map("monthly_payment") @db.Decimal(15, 2)
  remainingTermMonths Int    @map("remaining_term_months")
  nextPaymentDate   DateTime @map("next_payment_date")
  createdAt         DateTime @default(now()) @map("created_at")
  updatedAt         DateTime @updatedAt @map("updated_at")

  user    User     @relation(fields: [userId], references: [id], onDelete: Cascade)
  account Account? @relation(fields: [accountId], references: [id], onDelete: SetNull)

  @@index([userId])
  @@index([loanType])
  @@map("loans")
}

model Transaction {
  id            String   @id @default(uuid())
  userId        String   @map("user_id")
  accountId     String   @map("account_id") // Source account
  transactionType String @map("transaction_type") // "payment" | "transfer" | "deposit" | "withdrawal"
  amount        Decimal  @db.Decimal(15, 2)
  currency      String   @default("USD")
  fromAccount   String?  @map("from_account") // Source account number (for display)
  toAccount     String?  @map("to_account") // Destination account number or payment address
  beneficiaryId String?  @map("beneficiary_id") // Link to beneficiary if transfer to beneficiary
  description   String?
  status        String   @default("pending") // "pending" | "completed" | "failed" | "cancelled" | "expired"
  referenceNumber String? @unique @map("reference_number")
  paymentSessionId String? @unique @map("payment_session_id") // Links to OTP session
  expiresAt     DateTime? @map("expires_at") // Expiration time for pending transactions
  completedAt   DateTime? @map("completed_at") // Completion timestamp
  createdAt     DateTime @default(now()) @map("created_at")

  user        User         @relation(fields: [userId], references: [id], onDelete: Cascade)
  account     Account      @relation(fields: [accountId], references: [id], onDelete: Cascade)
  beneficiary Beneficiary? @relation(fields: [beneficiaryId], references: [id], onDelete: SetNull)

  @@index([userId])
  @@index([accountId])
  @@index([beneficiaryId])
  @@index([transactionType])
  @@index([status])
  @@index([paymentSessionId])
  @@index([createdAt])
  @@map("transactions")
}

model PaymentAlert {
  id            String   @id @default(uuid())
  userId        String   @map("user_id")
  alertType     String   @map("alert_type") // "payment_received" | "payment_sent" | "low_balance" | "high_balance"
  threshold     Decimal? @db.Decimal(15, 2) // For balance-based alerts
  accountId     String?  @map("account_id") // Optional: specific account
  isActive      Boolean  @default(true) @map("is_active")
  createdAt     DateTime @default(now()) @map("created_at")
  updatedAt     DateTime @updatedAt @map("updated_at")

  user User @relation(fields: [userId], references: [id], onDelete: Cascade)

  @@index([userId])
  @@index([alertType])
  @@index([isActive])
  @@map("payment_alerts")
}

model NotificationPreference {
  id            String   @id @default(uuid())
  userId        String   @map("user_id")
  channel       String   // "email" | "sms" | "push"
  eventType     String   @map("event_type") // "payment" | "alert" | "balance" | "transaction"
  isEnabled     Boolean  @default(true) @map("is_enabled")
  createdAt     DateTime @default(now()) @map("created_at")
  updatedAt     DateTime @updatedAt @map("updated_at")

  user User @relation(fields: [userId], references: [id], onDelete: Cascade)

  @@unique([userId, channel, eventType])
  @@index([userId])
  @@index([isEnabled])
  @@map("notification_preferences")
}
```

### Beneficiary Model Extension

The `Beneficiary` model already exists in the schema. Add the transaction relation:

```prisma
model Beneficiary {
  // ... existing fields ...
  transactions Transaction[] // Transactions sent to this beneficiary
}
```

### User Model Extension

Update existing `User` model to include relations:

```prisma
model User {
  // ... existing fields ...
  beneficiaries Beneficiary[]
  accounts      Account[]
  loans         Loan[]
  transactions  Transaction[]
  paymentAlerts PaymentAlert[]
  notificationPreferences NotificationPreference[]
}
```

### Beneficiary Integration with Transactions

**Key Relationships**:
- Transactions can be linked to beneficiaries via `beneficiaryId`
- When a transfer is made to a beneficiary, the transaction record includes:
  - `beneficiaryId`: Foreign key to beneficiary
  - `toAccount`: The beneficiary's `paymentAddress` (for display/audit)
  - Transaction type: "transfer" (external) vs "payment" (internal)

**Use Cases**:
1. **Transfer to Beneficiary by ID**: User provides `beneficiaryId`, system resolves payment address
2. **Transfer to Beneficiary by Nickname**: User provides `beneficiaryNickname`, system resolves to beneficiary and payment address
3. **Transfer History**: Users can query transactions filtered by `beneficiaryId` to see all payments to a specific beneficiary
4. **Voice Assistant Integration**: Voice commands like "Pay Mom $100" resolve nickname to beneficiary, then to payment address

### Migration Strategy

1. Create migration: `npx prisma migrate dev --name add_banking_models`
2. Update seed script to include banking data
3. Run seed: `pnpm db:seed`

---

## API Design

### Endpoint Structure

All endpoints under `/api/banking/` namespace:

#### Account Endpoints

**GET /api/banking/accounts**
- Retrieve all accounts for authenticated user
- Response: Array of account objects

**GET /api/banking/accounts/balance**
- Query params: `?accountType=checking` (optional)
- Retrieve balance(s) for specific account type or all accounts
- Response: Array of balance objects

#### Loan Endpoints

**GET /api/banking/loans**
- Retrieve all loans for authenticated user
- Response: Array of loan objects

#### Transaction Endpoints

**GET /api/banking/transactions**
- Query params:
  - `accountType` (optional): Filter by account type
  - `beneficiaryId` (optional): Filter transactions to specific beneficiary
  - `transactionType` (optional): Filter by type ("payment", "transfer", "deposit", "withdrawal")
  - `startDate` (optional): ISO 8601 date
  - `endDate` (optional): ISO 8601 date
  - `limit` (optional, default: 10): Pagination limit
  - `offset` (optional, default: 0): Pagination offset
- Response: Array of transaction objects with pagination metadata
- **Transaction Response includes**:
  - Full transaction details
  - Beneficiary information (if transaction linked to beneficiary)
  - Account information

#### Payment Endpoints (Two-Step Process)

**Step 1: POST /api/banking/payments/initiate**
- **Purpose**: Initiate a payment and generate OTP for confirmation
- Request body (supports multiple formats):
  ```json
  // Option 1: Transfer to beneficiary by ID
  {
    "fromAccount": "CHK-12345-001", // Account number or account type
    "beneficiaryId": "uuid-of-beneficiary",
    "amount": 100.00,
    "description": "Payment to Mom"
  }
  
  // Option 2: Transfer to beneficiary by nickname
  {
    "fromAccount": "CHK-12345-001",
    "beneficiaryNickname": "Mom",
    "amount": 100.00,
    "description": "Payment to Mom"
  }
  
  // Option 3: Transfer using paymentAddress (UPI ID or account number)
  {
    "fromAccount": "CHK-12345-001",
    "paymentAddress": "martha.doe@upi", // UPI ID or account number
    "amount": 100.00,
    "description": "Payment to Mom"
  }
  
  // Option 4: Internal transfer between own accounts
  {
    "fromAccount": "CHK-12345-001",
    "toAccount": "SAV-12345-002", // User's own account
    "amount": 500.00,
    "description": "Transfer to savings"
  }
  ```
- **Business Logic**:
  1. **Beneficiary Resolution** (if `beneficiaryId` or `beneficiaryNickname` provided):
     - Resolves beneficiary from user's beneficiaries
     - Extracts `paymentAddress` and `paymentType` from beneficiary
     - Uses beneficiary's `paymentAddress` for the transfer
     - Links transaction to beneficiary record via `beneficiaryId`
  
  2. **Direct Payment Address** (if `paymentAddress` provided):
     - Validates format (UPI ID pattern or account number)
     - Creates transaction without beneficiary link
     - Supports transfers to any UPI ID or account number
  
  3. **Internal Transfer Detection** (if `toAccount` provided):
     - Checks if `toAccount` belongs to user
     - If yes: Internal transfer (both accounts updated)
     - If no: External transfer (only source account updated)
  
  4. **Validations**:
     - Validates source account belongs to user
     - Checks sufficient balance in source account (reserved, not deducted)
     - Validates amount is positive
     - Creates transaction record with `status: "pending"`
  
  5. **OTP Generation**:
     - Generates 6-digit OTP code
     - Creates session ID: `payment_${transactionId}_${timestamp}`
     - Stores OTP in Redis with 5-minute TTL
     - Links OTP session to transaction ID
  
  6. **Response**:
     - Returns transaction object with `status: "pending"`
     - Returns `paymentSessionId` for OTP confirmation
     - Returns OTP code (development only) or sends via SMS/Email (production)
     - Includes transaction details for user confirmation
  
- **Response**:
  ```json
  {
    "transaction": {
      "id": "uuid",
      "status": "pending",
      "amount": 100.00,
      "fromAccount": "CHK-12345-001",
      "toAccount": "martha.doe@upi",
      "description": "Payment to Mom",
      "createdAt": "2025-01-XX..."
    },
    "paymentSessionId": "payment_uuid_timestamp",
    "message": "OTP sent to your registered email/phone",
    "otpCode": "123456" // Only in development mode
  }
  ```

**Step 2: POST /api/banking/payments/confirm**
- **Purpose**: Confirm payment by validating OTP and completing the transaction
- Request body:
  ```json
  {
    "paymentSessionId": "payment_uuid_timestamp",
    "otpCode": "123456"
  }
  ```
- **Business Logic**:
  1. **OTP Validation**:
     - Retrieves OTP from Redis using `paymentSessionId`
     - Validates OTP code matches
     - Checks OTP hasn't expired (5-minute TTL)
  
  2. **Transaction Retrieval**:
     - Retrieves pending transaction using session ID
     - Validates transaction belongs to authenticated user
     - Validates transaction status is still "pending"
     - Checks transaction hasn't expired (optional: 10-minute window)
  
  3. **Balance Validation** (re-check):
     - Re-validates source account has sufficient balance
     - Prevents race conditions if balance changed since initiation
  
  4. **Transaction Completion**:
     - **Internal Transfer**: Updates both source (debit) and destination (credit) account balances atomically
     - **External Transfer**: Updates only source account balance (debit)
     - Updates transaction status to `"completed"`
     - Generates reference number
     - Records completion timestamp
  
  5. **OTP Cleanup**:
     - Removes OTP from Redis after successful confirmation
     - Prevents OTP reuse
  
- **Response**:
  ```json
  {
    "transaction": {
      "id": "uuid",
      "status": "completed",
      "amount": 100.00,
      "fromAccount": "CHK-12345-001",
      "toAccount": "martha.doe@upi",
      "referenceNumber": "TXN-202501XX-ABC123",
      "completedAt": "2025-01-XX...",
      "beneficiary": { /* if applicable */ }
    },
    "message": "Payment completed successfully"
  }
  ```

**Error Scenarios**:
- Invalid OTP: Returns 400 with error message
- Expired OTP: Returns 400 with "OTP expired" message
- Transaction already completed: Returns 409 with "Payment already completed"
- Insufficient balance (re-check): Returns 400 with "Insufficient funds"
- Transaction not found: Returns 404 with "Payment session not found"

#### Alert Endpoints

**GET /api/banking/alerts**
- Retrieve all payment alerts for authenticated user
- Response: Array of alert objects

**POST /api/banking/alerts**
- Request body:
  ```json
  {
    "alertType": "low_balance",
    "threshold": 100.00,
    "accountId": "uuid" // Optional
  }
  ```
- Response: Created alert object

**PUT /api/banking/alerts/[id]**
- Update existing alert
- Response: Updated alert object

**DELETE /api/banking/alerts/[id]**
- Delete alert
- Response: 204 No Content

#### Notification Endpoints

**GET /api/banking/notifications**
- Retrieve all notification preferences for authenticated user
- Response: Array of notification preference objects

**POST /api/banking/notifications**
- Request body:
  ```json
  {
    "channel": "email",
    "eventType": "payment",
    "isEnabled": true
  }
  ```
- Response: Created notification preference object

**PUT /api/banking/notifications/[id]**
- Update notification preference
- Response: Updated notification preference object

**DELETE /api/banking/notifications/[id]**
- Delete notification preference
- Response: 204 No Content

### Response Format

**Success Response (200/201)**:
```json
{
  "data": { /* resource data */ },
  "meta": { /* pagination, if applicable */ }
}
```

**Error Response (4xx/5xx)**:
```json
{
  "error": "Error message",
  "code": "ERROR_CODE", // Optional
  "details": { /* Additional error details */ } // Optional
}
```

### Internal API Endpoints (for MCP Server)

**GET /api/internal/banking/accounts/[userId]**
- Requires: `X-API-Key` header
- Returns: Accounts for specified user (server-to-server)

**GET /api/internal/banking/transactions/[userId]**
- Requires: `X-API-Key` header
- Query params: Same as public endpoint
- Returns: Transactions for specified user (server-to-server)

---

## Beneficiary Integration Flow

### Overview

The Mock Bank APIs integrate seamlessly with the existing `/api/beneficiaries` endpoints to enable payments and transfers to saved beneficiaries. This integration supports the voice assistant use case where users can say "Pay Mom $100" and the system resolves "Mom" to a beneficiary's payment address.

### Integration Points

1. **Beneficiary Resolution**: Transfer endpoints accept beneficiary identifiers (ID or nickname) and resolve them to payment addresses
2. **Transaction Linking**: Transactions to beneficiaries are linked via `beneficiaryId` foreign key for history tracking
3. **Payment Address Extraction**: Beneficiary's `paymentAddress` and `paymentType` are used for the actual transfer

### Transfer Flow with Beneficiaries

```
**Step 1: Payment Initiation**
```
User Request: POST /api/banking/payments/initiate
{
  "fromAccount": "CHK-12345-001",
  "beneficiaryNickname": "Mom",
  "amount": 100.00
}

↓

1. Authenticate user (JWT validation)
2. Resolve payment destination:
   - Query beneficiaries table: WHERE userId = ? AND nickname = "Mom"
   - Extract: paymentAddress = "martha.doe@upi", paymentType = "upi"
   - beneficiaryId = resolved beneficiary ID
3. Validate source account belongs to user
4. Check sufficient balance (reserve, don't deduct)
5. Create pending transaction:
   - accountId: source account ID
   - beneficiaryId: resolved beneficiary ID (if beneficiary used)
   - toAccount: "martha.doe@upi" (from beneficiary.paymentAddress)
   - transactionType: "transfer" (external)
   - status: "pending"
   - expiresAt: 10 minutes from now
6. Generate 6-digit OTP
7. Create paymentSessionId: "payment_{transactionId}_{timestamp}"
8. Store OTP in Redis with paymentSessionId (5-minute TTL)
9. Return transaction with paymentSessionId and OTP
```

**Step 2: Payment Confirmation**
```
User Request: POST /api/banking/payments/confirm
{
  "paymentSessionId": "payment_uuid_timestamp",
  "otpCode": "123456"
}

↓

1. Authenticate user (JWT validation)
2. Validate OTP from Redis:
   - Retrieve OTP using paymentSessionId
   - Compare with provided otpCode
   - Check OTP hasn't expired
3. Retrieve pending transaction using paymentSessionId
4. Validate transaction belongs to user
5. Validate transaction status is "pending"
6. Re-check sufficient balance (prevent race conditions)
7. Complete transaction:
   - Update source account balance (debit)
   - Update transaction status to "completed"
   - Generate referenceNumber
   - Set completedAt timestamp
8. Remove OTP from Redis
9. Return completed transaction
```

### Beneficiary Resolution Logic

**Priority Order**:
1. If `beneficiaryId` provided → Direct lookup by ID
2. If `beneficiaryNickname` provided → Lookup by nickname for user
3. If `toAccount` provided directly → Use as-is (no beneficiary link)

**Implementation**:
```typescript
// lib/banking/beneficiaries.ts
export async function resolveBeneficiary(
  userId: string,
  identifier: { id?: string; nickname?: string }
): Promise<Beneficiary | null> {
  if (identifier.id) {
    return await prisma.beneficiary.findFirst({
      where: {
        id: identifier.id,
        userId: userId // Security: ensure beneficiary belongs to user
      }
    });
  }
  
  if (identifier.nickname) {
    return await prisma.beneficiary.findUnique({
      where: {
        userId_nickname: {
          userId: userId,
          nickname: identifier.nickname
        }
      }
    });
  }
  
  return null;
}
```

### Transaction History with Beneficiaries

When querying transactions, include beneficiary information:

```typescript
// GET /api/banking/transactions?beneficiaryId=uuid
const transactions = await prisma.transaction.findMany({
  where: {
    userId: user.user_id,
    beneficiaryId: beneficiaryId // Filter by beneficiary
  },
  include: {
    beneficiary: {
      select: {
        nickname: true,
        fullName: true,
        paymentAddress: true,
        paymentType: true
      }
    },
    account: {
      select: {
        accountNumber: true,
        accountType: true
      }
    }
  }
});
```

### Voice Assistant Integration

The MCP server's `get_transfer_contacts` tool already fetches beneficiaries. The banking transfer API complements this by:

1. **Accepting Beneficiary References**: Transfer endpoint accepts beneficiary ID or nickname
2. **Resolving to Payment Address**: Automatically extracts payment address from beneficiary
3. **Maintaining History**: Links transactions to beneficiaries for querying payment history

**Example Voice Flow (Two-Step)**:
```
User: "Pay Mom $100"
↓
Voice Agent → MCP: get_transfer_contacts() → Returns [{"nickname": "Mom", "paymentAddress": "martha.doe@upi", ...}]
↓
Voice Agent → MCP: make_payment(to_account="Mom") 
↓
MCP → Next.js API: POST /api/banking/payments/initiate { beneficiaryNickname: "Mom", ... }
↓
Next.js API:
  1. Resolves "Mom" → beneficiary → paymentAddress
  2. Creates pending transaction
  3. Generates OTP
  4. Returns: { transaction, paymentSessionId, otpCode }
↓
Voice Agent → User: "Please confirm payment of $100 to Mom. Enter OTP: 123456"
↓
User: Provides OTP
↓
Voice Agent → MCP: confirm_payment(sessionId, otpCode)
↓
MCP → Next.js API: POST /api/banking/payments/confirm { paymentSessionId, otpCode }
↓
Next.js API:
  1. Validates OTP
  2. Completes transaction
  3. Updates account balance
  4. Returns: { transaction: { status: "completed", ... } }
↓
Voice Agent → User: "Payment of $100 to Mom completed successfully. Reference: TXN-202501XX-ABC123"
```

**Alternative: Direct Payment Address**:
```
User: "Pay martha.doe@upi $100"
↓
Voice Agent → MCP: make_payment(to_account="martha.doe@upi")
↓
MCP → Next.js API: POST /api/banking/payments/initiate { paymentAddress: "martha.doe@upi", ... }
↓
[Same two-step flow with OTP confirmation]
```

---

## Authentication & Authorization

### Authentication Flow

All banking endpoints require JWT authentication:

1. Client includes `Authorization: Bearer <token>` header
2. Route handler extracts token via `extractTokenFromHeader()`
3. Token validated via `validateAccessToken()`
4. User identity extracted: `{ user_id, email, roles, permissions }`
5. Business logic uses `user_id` to scope data access

### Authorization Model

**User Scoping**: All queries automatically filtered by `userId` to ensure users can only access their own data.

**Permission Checks** (if needed):
- `read` permission: Required for GET endpoints
- `transact` permission: Required for POST /payments
- `configure` permission: Required for POST/PUT/DELETE on alerts and notifications

### MCP Server Integration

MCP server can access banking data via internal API endpoints using API key authentication:

```typescript
// MCP server calls Next.js API
const response = await fetch(
  `http://nextjs-server/api/internal/banking/accounts/${userId}`,
  {
    headers: {
      'X-API-Key': process.env.INTERNAL_API_KEY
    }
  }
);
```

---

## Database Architecture

### Database Design Principles

1. **User Isolation**: All tables include `userId` foreign key with cascade delete
2. **Audit Trail**: All tables include `createdAt` and `updatedAt` timestamps
3. **Indexing Strategy**: Indexes on foreign keys and frequently queried fields
4. **Data Types**: Use `Decimal` for monetary values to prevent floating-point errors
5. **Naming Convention**: Snake_case for database columns, camelCase for Prisma fields

### Transaction Management

For payment/transfer operations, use Prisma transactions to ensure atomicity:

**Payment Initiation (Step 1)**:
```typescript
// Step 1: Initiate payment
await prisma.$transaction(async (tx) => {
  // 1. Resolve payment destination:
  //    - If beneficiaryId/nickname: Resolve beneficiary, extract paymentAddress
  //    - If paymentAddress: Use directly
  //    - If toAccount: Check if belongs to user (internal) or external
  
  // 2. Validate source account belongs to user
  // 3. Validate source account has sufficient balance (reserve, don't deduct)
  
  // 4. Determine transaction type:
  //    - Internal: toAccount belongs to user
  //    - External: beneficiary or paymentAddress or external toAccount
  
  // 5. Create pending transaction record:
  //    - status: "pending"
  //    - Link to beneficiary if beneficiaryId resolved
  //    - Set toAccount to paymentAddress or account number
  //    - Set transactionType appropriately
  //    - Set expiresAt (10 minutes from now)
  
  // 6. Generate OTP and paymentSessionId
  // 7. Store OTP in Redis with paymentSessionId
  
  // Note: NO balance updates at this stage
});
```

**Payment Confirmation (Step 2)**:
```typescript
// Step 2: Confirm payment with OTP
await prisma.$transaction(async (tx) => {
  // 1. Validate OTP from Redis using paymentSessionId
  // 2. Retrieve pending transaction
  // 3. Re-validate source account has sufficient balance
  
  // 4. Update balances:
  //    - Internal: Update both source (debit) and destination (credit)
  //    - External: Update only source (debit)
  
  // 5. Update transaction record:
  //    - status: "completed"
  //    - Generate referenceNumber
  //    - Set completedAt timestamp
  
  // 6. Remove OTP from Redis
  
  // All or nothing
});
```

**Beneficiary Resolution in Payment**:
```typescript
// Resolve beneficiary if identifier provided
let beneficiary = null;
let paymentAddress = null;
let paymentType = null;

if (beneficiaryId || beneficiaryNickname) {
  beneficiary = await resolveBeneficiary(userId, {
    id: beneficiaryId,
    nickname: beneficiaryNickname
  });
  
  if (!beneficiary) {
    throw new Error('Beneficiary not found');
  }
  
  paymentAddress = beneficiary.paymentAddress;
  paymentType = beneficiary.paymentType;
} else if (paymentAddressParam) {
  // Use provided paymentAddress directly
  paymentAddress = paymentAddressParam;
  paymentType = detectPaymentType(paymentAddress); // "upi" or "account"
} else if (toAccount) {
  // Check if toAccount belongs to user (internal) or external
  const destinationAccount = await findAccountByNumber(toAccount);
  if (destinationAccount && destinationAccount.userId === userId) {
    // Internal transfer
    paymentAddress = toAccount;
    paymentType = "account";
  } else {
    // External transfer
    paymentAddress = toAccount;
    paymentType = detectPaymentType(toAccount);
  }
}
```

### Concurrency Control

For balance updates, use optimistic locking or database-level locks to prevent race conditions:

```typescript
// Option 1: Optimistic locking with version field
// Option 2: SELECT FOR UPDATE (PostgreSQL row-level lock)
const account = await prisma.$queryRaw`
  SELECT * FROM accounts 
  WHERE id = ${accountId} 
  FOR UPDATE
`;
```

---

## Error Handling & Validation

### Error Response Standards

Follow existing error handling patterns:

```typescript
// Authentication error
return corsResponse(
  { error: 'Unauthorized', code: 'AUTH_REQUIRED' },
  401
);

// Validation error
return corsResponse(
  { error: 'Invalid request', code: 'VALIDATION_ERROR', details: { field: 'amount', message: 'Amount must be positive' } },
  400
);

// Not found
return corsResponse(
  { error: 'Account not found', code: 'NOT_FOUND' },
  404
);

// Insufficient funds
return corsResponse(
  { error: 'Insufficient funds', code: 'INSUFFICIENT_FUNDS' },
  400
);

// Server error
return corsResponse(
  { error: 'Internal server error', code: 'INTERNAL_ERROR' },
  500
);
```

### Validation Rules

**Account Operations**:
- Account must belong to authenticated user
- Account status must be "active"

**Payment Initiation**:
- Amount must be positive
- Source account must have sufficient balance (checked but not deducted)
- Credit card transfers must respect credit limit
- Source account must belong to authenticated user
- Transaction expires after 10 minutes if not confirmed

**Payment Confirmation**:
- OTP must be valid 6-digit numeric code
- OTP must match stored OTP for paymentSessionId
- OTP expires after 5 minutes
- Payment session must exist and be linked to pending transaction
- Transaction must be in "pending" status
- Transaction must not be expired
- Source account must still have sufficient balance (re-checked)

**Beneficiary-Based Payments**:
- If `beneficiaryId` provided: Must belong to authenticated user
- If `beneficiaryNickname` provided: Must exist and belong to authenticated user
- Beneficiary must have valid `paymentAddress` and `paymentType`

**Direct Payment Address**:
- If `paymentAddress` provided: Must be valid UPI ID format (e.g., `name@upi`) or account number
- UPI ID validation: Must match pattern `^[a-zA-Z0-9._-]+@[a-zA-Z0-9]+$`

**Internal Transfers**:
- If `toAccount` provided and belongs to user: Both accounts must belong to authenticated user
- Source and destination accounts must be different
- Both account balances updated atomically

**External Transfers**:
- If `toAccount` provided and doesn't belong to user: Only source account balance updated
- `toAccount` must be valid account number or UPI ID

**Beneficiary Resolution**:
- `beneficiaryId` takes precedence over `beneficiaryNickname`
- If both provided, `beneficiaryId` is used
- Beneficiary must belong to authenticated user
- Beneficiary must have valid `paymentAddress` and `paymentType`

**Date Range Validation**:
- `startDate` must be before `endDate`
- Date range cannot exceed 1 year (configurable)
- `scheduledDate` must be in the future

**Pagination Validation**:
- `limit` must be between 1 and 100
- `offset` must be non-negative

---

## Source Tree Organization

### New File Structure

```
agent-starter-react/
├── app/
│   └── api/
│       └── banking/                    # NEW: Banking API routes
│           ├── accounts/
│           │   ├── route.ts           # GET /api/banking/accounts
│           │   └── balance/
│           │       └── route.ts       # GET /api/banking/accounts/balance
│           ├── loans/
│           │   └── route.ts           # GET /api/banking/loans
│           ├── transactions/
│           │   └── route.ts           # GET /api/banking/transactions
│           ├── payments/
│           │   ├── route.ts           # (not used - see sub-routes)
│           │   ├── initiate/
│           │   │   └── route.ts      # POST /api/banking/payments/initiate
│           │   └── confirm/
│           │       └── route.ts       # POST /api/banking/payments/confirm
│           ├── alerts/
│           │   ├── route.ts           # GET, POST /api/banking/alerts
│           │   └── [id]/
│           │       └── route.ts        # PUT, DELETE /api/banking/alerts/[id]
│           └── notifications/
│               ├── route.ts            # GET, POST /api/banking/notifications
│               └── [id]/
│                   └── route.ts        # PUT, DELETE /api/banking/notifications/[id]
│       └── internal/                 # EXISTING: Internal API routes
│           └── banking/               # NEW: Internal banking endpoints
│               ├── accounts/
│               │   └── [userId]/
│               │       └── route.ts   # GET /api/internal/banking/accounts/[userId]
│               └── transactions/
│                   └── [userId]/
│                       └── route.ts   # GET /api/internal/banking/transactions/[userId]
├── lib/
│   ├── auth.ts                        # EXISTING: Authentication utilities
│   ├── cors.ts                        # EXISTING: CORS utilities
│   ├── db/
│   │   └── prisma.ts                  # EXISTING: Prisma client
│   └── banking/                       # NEW: Banking business logic
│       ├── accounts.ts
│       ├── loans.ts
│       ├── transactions.ts
│       ├── payments.ts
│       ├── transfers.ts
│       ├── beneficiaries.ts           # Beneficiary resolution and lookup
│       ├── alerts.ts
│       ├── notifications.ts
│       └── validators.ts
└── prisma/
    ├── schema.prisma                  # MODIFIED: Add banking models
    ├── migrations/                    # NEW: Migration files
    └── seed.ts                        # MODIFIED: Add banking seed data
```

### Code Organization Principles

1. **Route Handlers**: Thin controllers that handle HTTP concerns (auth, validation, response formatting)
2. **Business Logic**: Separated into `lib/banking/` for testability
3. **Validation**: Centralized in `validators.ts` for consistency
4. **Type Definitions**: Shared types in route handlers and business logic

---

## Testing Strategy

### Unit Tests

**Location**: `__tests__/api/banking/` and `__tests__/lib/banking/`

**Coverage**:
- Route handler authentication/authorization
- Business logic functions
- Validation functions
- Error handling

**Example**:
```typescript
describe('GET /api/banking/accounts', () => {
  it('should return 401 without authentication', async () => {
    const response = await fetch('/api/banking/accounts');
    expect(response.status).toBe(401);
  });

  it('should return user accounts with valid token', async () => {
    const token = await getTestToken();
    const response = await fetch('/api/banking/accounts', {
      headers: { Authorization: `Bearer ${token}` }
    });
    expect(response.status).toBe(200);
    const data = await response.json();
    expect(Array.isArray(data.data)).toBe(true);
  });
});
```

### Integration Tests

**Location**: `__tests__/integration/banking/`

**Coverage**:
- End-to-end API flows
- Database transactions
- Concurrent operation handling
- Error scenarios

### Test Data Management

- Use test database (separate from development)
- Seed test data before each test suite
- Clean up after tests
- Use factories for test data generation

---

## Deployment Integration

### Database Migrations

1. **Development**: `npx prisma migrate dev`
2. **Staging/Production**: `npx prisma migrate deploy`
3. **Rollback**: Create reverse migration if needed

### Environment Variables

No new environment variables required - uses existing:
- `DATABASE_URL` (existing)
- `AUTH_SECRET_KEY` (existing)
- `INTERNAL_API_KEY` (existing, for MCP server)

### Deployment Process

1. Run database migrations
2. Deploy Next.js application (existing process)
3. Verify health check endpoint
4. Run smoke tests on banking endpoints

### Monitoring

- Add banking-specific metrics:
  - API endpoint response times
  - Payment/transfer success rates
  - Error rates by endpoint
- Use existing logging infrastructure
- Monitor database query performance

---

## Conclusion

This architecture document provides a comprehensive specification for integrating Mock Bank APIs into the existing Next.js authentication server. The design ensures:

- **Seamless Integration**: Follows existing patterns and conventions
- **Security**: Leverages existing authentication and authorization
- **Maintainability**: Clear separation of concerns and organized code structure
- **Testability**: Business logic separated from route handlers
- **Scalability**: Efficient database queries with proper indexing

**Next Steps**:
1. Implement database schema migrations
2. Create seed data for development/testing
3. Implement API endpoints following this architecture
4. Add comprehensive tests
5. Integrate with MCP server for voice assistant support

---

**Document Status:** Ready for Implementation  
**Related Documents:** [Mock Bank APIs PRD](./prd.md), [Main Architecture Document](../architecture.md)

