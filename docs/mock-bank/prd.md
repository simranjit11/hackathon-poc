# Mock Bank APIs Product Requirements Document (PRD)

## Goals and Background Context

### Goals

- Enable comprehensive banking operations through RESTful API endpoints for development and testing
- Provide mock banking data and operations that simulate real-world banking scenarios
- Support voice assistant integration with reliable, predictable banking data responses
- Enable payment processing with two-step OTP confirmation and account management
- Enable reminder functionality for future scheduled payments
- Create a foundation for testing banking workflows without external dependencies

### Background Context

The project currently has a voice assistant system that integrates with banking services through an MCP (Model Context Protocol) server. While basic banking operations exist (account viewing, transactions, loans), there's a need to expand and formalize the mock bank APIs to support a complete set of banking functionalities. This PRD addresses the need for a comprehensive mock banking API that can support:

1. **Development and Testing**: Developers need reliable mock APIs to test banking workflows without connecting to production banking systems
2. **Voice Assistant Integration**: The voice agent requires structured, predictable responses from banking APIs to provide accurate information to users
3. **Feature Completeness**: Current implementation has basic read operations, but needs payment processing and transfer capabilities

The mock bank APIs will serve as a critical component in the development workflow, allowing teams to build and test banking features independently of external banking service dependencies. This is particularly important for the voice assistant use case, where natural language queries about accounts, balances, transactions, loans, and payments need to be supported with accurate, consistent data.

### Change Log

| Date | Version | Description | Author |
|------|---------|-------------|--------|
| 2025-01-XX | 1.0 | Initial PRD creation | PM Agent |
| 2025-01-XX | 1.1 | Removed notifications and payment alerts, added payment reminders | PM Agent |

## Requirements

### Functional

1. FR1: The system shall provide an API endpoint to retrieve account details for authenticated users, including account number, account type (checking, savings, credit card), account status, and creation date.

2. FR2: The system shall provide an API endpoint to retrieve current account balance for a specific account or all accounts belonging to an authenticated user.

3. FR3: The system shall provide an API endpoint to retrieve loan information for authenticated users, including loan type, outstanding balance, interest rate, monthly payment amount, remaining term, and next payment date.

4. FR4: The system shall provide an API endpoint to retrieve transaction history with support for filtering by account type, date range, and pagination (limit/offset).

5. FR5: The system shall provide an API endpoint to initiate payments (step 1), creating a pending transaction with OTP generation for confirmation. The endpoint shall support payments to beneficiaries (by ID or nickname), external accounts (by payment address), or internal transfers between user's own accounts.

6. FR6: The system shall provide an API endpoint to confirm payments (step 2) by validating the OTP code, completing the transaction, and updating account balances atomically. The endpoint shall support both internal transfers (updating both source and destination accounts) and external transfers (updating only source account).

7. FR7: The system shall provide an API endpoint to create, read, update, and delete reminders for future payments, including scheduled payment date, amount, recipient, and reminder notification settings.

8. FR8: The system shall validate all API requests for proper authentication and authorization, ensuring users can only access their own account data.

9. FR9: The system shall return consistent, structured JSON responses for all API endpoints with appropriate HTTP status codes and error messages.

10. FR10: The system shall maintain transaction history for all payments and transfers, including transaction ID, timestamp, amount, from/to accounts, and status.

11. FR11: The system shall support mock data persistence across API calls within a session or configured time period to simulate realistic banking behavior.

### Non Functional

1. NFR1: All API endpoints shall respond within 200ms for read operations and 500ms for write operations under normal load conditions.

2. NFR2: The API shall follow RESTful design principles with clear, consistent URL patterns and HTTP method usage (GET for reads, POST for creates, PUT/PATCH for updates, DELETE for deletes).

3. NFR3: All API responses shall use standard HTTP status codes (200 for success, 400 for bad request, 401 for unauthorized, 404 for not found, 500 for server errors).

4. NFR4: The system shall provide comprehensive error responses with clear error messages and error codes to aid in debugging and integration.

5. NFR5: The API shall support JSON request and response formats with proper content-type headers.

6. NFR6: The system shall be designed to be easily extensible for adding new account types or transaction types without major refactoring.

7. NFR7: The mock data shall be configurable and seedable to support different testing scenarios and use cases.

8. NFR8: The API documentation shall be provided in OpenAPI/Swagger format for easy integration and testing.

9. NFR9: The system shall maintain data consistency for concurrent operations (e.g., preventing double-spending in payment scenarios).

10. NFR10: The API shall be compatible with the existing MCP server architecture and authentication mechanisms.

11. NFR11: The API endpoints shall be implemented as Next.js API routes using the App Router pattern (route.ts files) within the existing Next.js authentication server.

12. NFR12: The API shall leverage existing authentication middleware (`validateAccessToken`, `extractTokenFromHeader`) and CORS utilities (`corsResponse`, `corsPreflight`) from the Next.js server.

## User Interface Design Goals

_Not applicable - This PRD is for API-only functionality. No UI requirements._

## Technical Assumptions

### Repository Structure: Monorepo

The project uses a monorepo structure with the Next.js server located in `agent-starter-react/`. The mock banking APIs will be added to this existing Next.js application.

### Service Architecture

**Next.js API Routes (App Router)**: The mock banking APIs will be implemented as Next.js API route handlers following the existing pattern:
- Route files: `app/api/banking/.../route.ts`
- Authentication: Reuse existing `validateAccessToken` and `extractTokenFromHeader` from `@/lib/auth`
- CORS: Reuse existing `corsResponse` and `corsPreflight` from `@/lib/cors`
- Database: Use existing Prisma client with PostgreSQL database

**API Endpoint Structure**:
- `GET /api/banking/accounts` - Retrieve account details
- `GET /api/banking/accounts/balance` - Retrieve account balance(s)
- `GET /api/banking/loans` - Retrieve loan information
- `GET /api/banking/transactions` - Retrieve transaction history
- `POST /api/banking/payments/initiate` - Initiate payments (creates pending transaction with OTP)
- `POST /api/banking/payments/confirm` - Confirm payments with OTP
- `GET /api/banking/reminders` - Retrieve payment reminders
- `POST /api/banking/reminders` - Create payment reminder
- `PUT /api/banking/reminders/[id]` - Update payment reminder
- `DELETE /api/banking/reminders/[id]` - Delete payment reminder

### Testing Requirements

**Unit + Integration Testing**: 
- Unit tests for individual API route handlers
- Integration tests for API endpoints with authentication
- Mock data setup and teardown for testing scenarios
- Test utilities for generating authenticated requests

### Additional Technical Assumptions and Requests

1. **Database Schema**: Extend existing Prisma schema with new models for:
   - `Account` - User banking accounts (checking, savings, credit card)
   - `Loan` - User loan information
   - `Transaction` - Payment and transfer transaction history
   - `PaymentReminder` - Reminders for future scheduled payments

2. **Authentication**: All banking API endpoints will require valid JWT token in Authorization header, following the existing pattern used in `/api/beneficiaries` and `/api/auth/me`.

3. **Data Persistence**: Use PostgreSQL database (via Prisma) for persistent storage of accounts, transactions, loans, and payment reminders. Mock data can be seeded via Prisma seed script.

4. **Error Handling**: Follow existing error handling patterns with consistent JSON error responses and appropriate HTTP status codes.

5. **TypeScript**: All API routes and business logic will be written in TypeScript with proper type definitions.

6. **MCP Server Integration**: The MCP server can call these Next.js API endpoints using the existing internal API key authentication mechanism (similar to `/api/internal/users/[id]`) or via user JWT tokens.

7. **Mock Data Seeding**: Provide seed data script to populate initial accounts, loans, and transactions for development and testing purposes.

## Epic List

1. **Epic 1: Database Schema and Foundation**: Establish Prisma database schema for banking entities (accounts, loans, transactions, payment reminders) and create seed data for development/testing.

2. **Epic 2: Account and Balance Read Operations**: Implement API endpoints for retrieving account details and account balances with proper authentication and authorization.

3. **Epic 3: Loans and Transactions Read Operations**: Implement API endpoints for retrieving loan information and transaction history with filtering and pagination support.

4. **Epic 4: Payment and Transfer Operations**: Implement API endpoints for initiating payments (with OTP) and confirming payments (with OTP validation), including validation, balance checks, and transaction recording.

5. **Epic 5: Payment Reminders Management**: Implement CRUD API endpoints for payment reminders (for future scheduled payments).


