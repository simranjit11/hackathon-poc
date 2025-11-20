# Elicitation Flow Testing Procedure

## Overview
This document provides step-by-step testing procedures for the MCP elicitation flow (Story 2.2).

---

## Prerequisites

### Required Services
1. **Redis** - Running on localhost:6379 (or configured host)
2. **MCP Server** - Running on port 8001
3. **Next.js Server** - Running on port 3000 (agent-starter-react)
4. **LiveKit Server** - Running (for full integration tests)

### Environment Variables
Ensure these are set in your `.env` files:

```bash
# Redis Configuration
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=
REDIS_DB=0

# Elicitation Configuration
ELICITATION_TIMEOUT_SECONDS=300  # 5 minutes

# MCP Server
MCP_SERVER_URL=http://localhost:8001/mcp
MCP_JWT_SECRET_KEY=your-secret-key-change-in-production
```

---

## Test 1: Elicitation Schema Creation

### Objective
Verify that elicitation schemas are created correctly.

### Steps

1. **Test OTP Schema Creation**
```python
# In Python console or test file
from schemas.elicitation import create_otp_elicitation, ElicitationContext

context = ElicitationContext(
    amount="₹1,500.00",
    payee="John Doe",
    account="Checking ****1234"
)

schema = create_otp_elicitation(
    elicitation_id="test-123",
    context=context,
    platform="web"
)

print(schema.model_dump_json(indent=2))
```

### Expected Result
- Schema should have `elicitation_type: "otp"`
- Should have one field: `otp_code` with 6-digit validation
- Context should be properly populated
- Platform requirements should show `biometric_required: False` for web

### Validation
✅ Schema structure matches `ElicitationSchema` model  
✅ All required fields present  
✅ Validation rules correctly defined

---

## Test 2: Redis State Management

### Objective
Verify elicitation state storage and retrieval in Redis.

### Steps

1. **Start Redis**
```bash
redis-server
```

2. **Test State Creation**
```python
from elicitation_manager import get_elicitation_manager
from schemas.elicitation import create_otp_elicitation, ElicitationContext
from datetime import datetime
import uuid

manager = get_elicitation_manager()

# Create schema
context = ElicitationContext(
    amount="₹2,000.00",
    payee="Alice Smith",
    account="Savings ****5678"
)

schema = create_otp_elicitation(
    elicitation_id=str(uuid.uuid4()),
    context=context
)

# Store in Redis
state = manager.create_elicitation(
    tool_call_id="tool-123",
    mcp_endpoint="make_payment_with_elicitation",
    user_id="user-456",
    session_id="session-789",
    room_name="room-abc",
    schema=schema,
    suspended_tool_arguments={
        "from_account": "checking",
        "to_account": "1234567890",
        "amount": 2000.0
    }
)

print(f"Created elicitation: {state.elicitation_id}")
```

3. **Test State Retrieval**
```python
# Retrieve from Redis
retrieved = manager.get_elicitation(state.elicitation_id)
print(f"Status: {retrieved.status}")
print(f"Expires at: {retrieved.expires_at}")
```

4. **Test Queue Management**
```python
# Check queue
queue_length = manager.get_queue_length("session-789")
print(f"Queue length: {queue_length}")

next_id = manager.get_next_in_queue("session-789")
print(f"Next in queue: {next_id}")
```

5. **Verify in Redis CLI**
```bash
redis-cli
> KEYS elicitation:*
> HGETALL elicitation:<your-elicitation-id>
> LRANGE elicitation_queue:session-789 0 -1
```

### Expected Results
✅ State stored successfully in Redis  
✅ State can be retrieved with all fields intact  
✅ Elicitation added to queue  
✅ TTL set correctly (300 seconds + 60s buffer)

---

## Test 3: MCP Tool Elicitation Response

### Objective
Verify MCP tool returns elicitation response instead of immediate payment.

### Steps

1. **Start MCP Server**
```bash
cd mcp-server
python main.py
```

2. **Test Tool Call** (using curl or Postman)
```bash
# Generate JWT token first
python mcp-server/generate_jwt.py

# Call the elicitation-enabled payment tool
curl -X POST http://localhost:8001/mcp \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <YOUR_JWT_TOKEN>" \
  -d '{
    "jsonrpc": "2.0",
    "id": 1,
    "method": "tools/call",
    "params": {
      "name": "make_payment_with_elicitation",
      "arguments": {
        "jwt_token": "<YOUR_JWT_TOKEN>",
        "from_account": "checking",
        "to_account": "Bob Johnson",
        "amount": 1500.0,
        "description": "Test payment"
      }
    }
  }'
```

### Expected Response
```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "result": {
    "status": "elicitation_required",
    "elicitation_id": "<UUID>",
    "tool_call_id": "<UUID>",
    "schema": {
      "elicitation_id": "<UUID>",
      "elicitation_type": "otp",
      "fields": [...],
      "context": {
        "amount": "₹1,500.00",
        "payee": "Bob ****son",
        "account": "Checking"
      }
    },
    "suspended_arguments": {
      "user_id": "...",
      "from_account": "checking",
      "to_account": "Bob Johnson",
      "amount": 1500.0
    }
  }
}
```

### Validation
✅ Response status is `elicitation_required`  
✅ Schema is properly formatted  
✅ Suspended arguments captured  
✅ Amount >= 1000 triggers OTP, < 1000 triggers confirmation

---

## Test 4: Next.js Elicitation Endpoints

### Objective
Test the Next.js API routes for resume and cancel operations.

### Steps

1. **Start Next.js Server**
```bash
cd agent-starter-react
npm run dev
```

2. **Test Resume Endpoint**
```bash
curl -X POST http://localhost:3000/api/elicitation/resume \
  -H "Content-Type: application/json" \
  -d '{
    "elicitation_id": "test-elicitation-123",
    "tool_call_id": "tool-call-456",
    "user_input": {
      "otp_code": "123456"
    },
    "suspended_arguments": {
      "user_id": "user-789",
      "from_account": "checking",
      "to_account": "Alice",
      "amount": 1500.0,
      "description": "Test payment"
    }
  }'
```

**Expected Response (Valid OTP)**:
```json
{
  "status": "completed",
  "payment_result": {
    "status": "completed",
    "confirmation_number": "TXNABC123XYZ",
    "from_account": "checking",
    "to_account": "Alice",
    "amount": 1500.0,
    "message": "Payment processed successfully"
  }
}
```

**Test Invalid OTP**:
```bash
curl -X POST http://localhost:3000/api/elicitation/resume \
  -H "Content-Type: application/json" \
  -d '{
    "elicitation_id": "test-elicitation-123",
    "tool_call_id": "tool-call-456",
    "user_input": {
      "otp_code": "999999"
    },
    "suspended_arguments": {
      "user_id": "user-789",
      "from_account": "checking",
      "to_account": "Alice",
      "amount": 1500.0
    }
  }'
```

**Expected Response (Invalid OTP)**:
```json
{
  "status": "failed",
  "error": "Invalid OTP code. Please try again."
}
```

3. **Test Cancel Endpoint**
```bash
curl -X POST http://localhost:3000/api/elicitation/550e8400-e29b-41d4-a716-446655440000/cancel \
  -H "Content-Type: application/json" \
  -d '{
    "reason": "User cancelled the payment"
  }'
```

**Expected Response**:
```json
{
  "status": "cancelled",
  "elicitation_id": "550e8400-e29b-41d4-a716-446655440000",
  "reason": "User cancelled the payment"
}
```

### Validation
✅ Valid OTP (123456) completes payment  
✅ Invalid OTP returns error  
✅ Confirmation (confirmed: true) completes payment  
✅ Cancel endpoint works correctly

---

## Test 5: Expiration Cleanup

### Objective
Verify expired elicitations are automatically cleaned up.

### Steps

1. **Create Short-Lived Elicitation**
```python
from elicitation_manager import get_elicitation_manager
from schemas.elicitation import create_otp_elicitation, ElicitationContext
import uuid

manager = get_elicitation_manager()

schema = create_otp_elicitation(
    elicitation_id=str(uuid.uuid4()),
    context=ElicitationContext(
        amount="₹1,000.00",
        payee="Test",
        account="Test"
    )
)

# Create with 10 second timeout
state = manager.create_elicitation(
    tool_call_id="test",
    mcp_endpoint="test",
    user_id="user-test",
    session_id="session-test",
    room_name="room-test",
    schema=schema,
    suspended_tool_arguments={},
    timeout_seconds=10  # 10 seconds
)

print(f"Created elicitation: {state.elicitation_id}")
print("Wait 15 seconds...")
```

2. **Start Cleanup Task**
```python
from elicitation_cleanup import start_cleanup_task
import asyncio

async def test_cleanup():
    await start_cleanup_task(check_interval_seconds=5)
    await asyncio.sleep(20)  # Let it run for 20 seconds

asyncio.run(test_cleanup())
```

3. **Check Logs**
Should see:
```
Found 1 expired elicitations
Marked elicitation <id> as expired
```

4. **Verify in Redis**
```bash
redis-cli
> HGET elicitation:<your-id> status
# Should return "expired"
```

### Validation
✅ Cleanup task finds expired elicitations  
✅ Status updated to "expired"  
✅ Removed from queue  
✅ Runs on schedule

---

## Test 6: Sequential Queue Management

### Objective
Verify only one elicitation is processed at a time per session.

### Steps

1. **Create Multiple Elicitations**
```python
from elicitation_manager import get_elicitation_manager
from schemas.elicitation import create_otp_elicitation, ElicitationContext
import uuid

manager = get_elicitation_manager()
session_id = "test-session-123"

# Create 3 elicitations
for i in range(3):
    schema = create_otp_elicitation(
        elicitation_id=str(uuid.uuid4()),
        context=ElicitationContext(
            amount=f"₹{(i+1)*1000}.00",
            payee=f"Payee {i+1}",
            account="Test"
        )
    )
    
    manager.create_elicitation(
        tool_call_id=f"tool-{i}",
        mcp_endpoint="test",
        user_id="user-test",
        session_id=session_id,
        room_name="room-test",
        schema=schema,
        suspended_tool_arguments={}
    )

# Check queue
print(f"Queue length: {manager.get_queue_length(session_id)}")
print(f"Next in queue: {manager.get_next_in_queue(session_id)}")
```

2. **Process Queue**
```python
# Get next
next_id = manager.get_next_in_queue(session_id)
print(f"Processing: {next_id}")

# Complete it
manager.update_elicitation_status(next_id, ElicitationStatus.COMPLETED)
manager.remove_from_queue(session_id, next_id)

# Check queue again
print(f"Queue length after: {manager.get_queue_length(session_id)}")
print(f"Next in queue: {manager.get_next_in_queue(session_id)}")
```

### Expected Results
✅ All 3 elicitations added to queue  
✅ Queue length = 3  
✅ First elicitation is at front of queue  
✅ After removal, queue length = 2  
✅ Next elicitation moves to front

---

## Test 7: Integration Test (Full Flow)

### Objective
Test complete elicitation flow from MCP tool to frontend response.

### Manual Test Steps

1. **Trigger Payment from Voice Agent**
   - Start voice session
   - Say: "Send ₹1500 to John"
   - Agent should call `make_payment_with_elicitation` tool

2. **Verify Elicitation Created**
   - Check Redis for elicitation state
   - Check logs for "Created elicitation" message

3. **Frontend Receives Elicitation** (to be implemented in Story 2.3)
   - Data channel message with elicitation schema
   - UI renders OTP input

4. **User Provides OTP**
   - Enter "123456"
   - Submit to `/api/elicitation/resume`

5. **Payment Completes**
   - Receive confirmation
   - Status updated to completed
   - Removed from queue

### Validation
✅ End-to-end flow works  
✅ State managed correctly  
✅ No memory leaks  
✅ Error handling works

---

## Acceptance Criteria Verification

### AC1: MCP tool can return `create_elicitation` response
✅ Tested in Test 3  
✅ `make_payment_with_elicitation` tool returns proper schema

### AC2: Elicitation schema defines required fields
✅ Tested in Test 1  
✅ OTP, confirmation, supervisor approval schemas defined

### AC3: State stored in Redis with expiration
✅ Tested in Test 2  
✅ TTL set to 300 seconds (5 minutes)

### AC4: Linked to original request via trace ID
✅ Tested in Test 2  
✅ `tool_call_id` links elicitation to suspended tool

### AC5: Sequential queue processes one at a time
✅ Tested in Test 6  
✅ FIFO queue implemented with Redis lists

### AC6: Elicitation can be cancelled
✅ Tested in Test 4  
✅ Cancel endpoint implemented

### AC7: Expired elicitations cleaned up automatically
✅ Tested in Test 5  
✅ Background task marks expired and cleans up

---

## Common Issues & Troubleshooting

### Issue: Redis connection fails
**Solution**: 
- Check Redis is running: `redis-cli ping`
- Verify REDIS_HOST and REDIS_PORT in .env

### Issue: Elicitation not found
**Solution**:
- Check TTL hasn't expired
- Verify elicitation_id is correct UUID
- Check Redis: `redis-cli KEYS elicitation:*`

### Issue: Queue not processing correctly
**Solution**:
- Check queue: `redis-cli LRANGE elicitation_queue:<session_id> 0 -1`
- Verify remove_from_queue is called after completion

### Issue: MCP tool returns 401 Unauthorized
**Solution**:
- Regenerate JWT token
- Verify JWT_SECRET_KEY matches between orchestrator and MCP server
- Check token has "transact" scope

---

## Next Steps

After Story 2.2 is complete, proceed to:
- **Story 2.3**: Elicitation UI Web (render elicitation in frontend)
- **Story 2.5**: Elicitation Response Handling (integrate with orchestrator)


