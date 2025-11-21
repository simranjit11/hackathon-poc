# Voice-Based UX Enhancement PRD

**Version:** 1.0  
**Last Updated:** 2025-11-20  
**Status:** Ready for Implementation  
**Project Type:** Hackathon POC

---

## Problem Statement

### Current Behavior

**User**: "What are my user details?"

**Agent**: *[2-3 seconds of awkward silence while MCP call executes]*

**Agent**: "Your user ID is 12345, email is john at example dot com, roles array contains customer, permissions array contains read, transact, configure..."

### Issues

1. **Awkward Silences**: No acknowledgment before tool execution makes users think the system is broken
2. **Data Dumps**: Raw JSON recited verbally is impossible to understand
3. **Poor Voice UX**: Behaves like a text chatbot with TTS, not a natural voice interface

### Desired Behavior

**User**: "What are my user details?"

**Agent**: "Let me fetch your profile details." *[Immediate]*

**Agent**: "I can see you're registered as John Smith, with the email john@example.com. Your account has full customer access."

---

## Goals

1. **Eliminate Awkward Silences**: Provide immediate verbal acknowledgment before tool calls
2. **Natural Voice Responses**: Convert JSON to conversational language
3. **Simple Implementation**: Leverage existing architecture with minimal changes

---

## Solution Approach

### Option 1: Enhanced Agno Instructions (Recommended - Simple)

Improve the Agno agent instructions to naturally include acknowledgments and format responses conversationally.

**Implementation**: Update agent instructions in `agent.py`

```python
instructions = """You are a helpful and professional banking voice assistant.

IMPORTANT VOICE UX GUIDELINES:

1. ALWAYS acknowledge before calling tools:
   - Before checking balance: "Let me check your balance"
   - Before getting details: "Let me fetch that information"
   - Before transactions: "Let me pull up your transaction history"
   - Before payments: "Let me process that payment"

2. Format ALL responses for voice (NOT raw data):
   ✓ "You have three accounts totaling $5,240"
   ✗ "accounts: [{'type': 'checking', 'balance': 2500}, ...]"
   
3. Keep responses conversational and concise:
   - Use natural language
   - Summarize key points first
   - Avoid technical jargon

Remember: Users are LISTENING, not reading. Make it sound natural!
"""
```

**Pros**: 
- Simple to implement (just update instructions)
- No architectural changes
- Works within existing Agno framework

**Cons**: 
- Relies on LLM following instructions consistently
- May need iteration to get right

### Option 2: Response Formatting Layer (Advanced - More Control)

Add post-processing to format Agno responses if instructions alone aren't sufficient.

**Implementation**: Enhance `llm_node()` in `agent.py`

```python
async def llm_node(...):
    response = await self.agno_agent.arun(user_message)
    
    # Post-process if response contains raw data
    formatted_text = format_for_voice(response.content)
    
    async def agno_response_stream():
        for chunk in formatted_text:
            yield sanitize_text(chunk)
    
    return agno_response_stream()
```

**Pros**: 
- Guaranteed formatting
- More control over output

**Cons**: 
- More code to maintain
- Need to handle all tool response types

---

## Requirements

### Functional Requirements

**FR1: Conversational Acknowledgments**
- Agent provides verbal acknowledgment before each tool call
- Acknowledgment is contextual to the operation
- Example: "Let me check your balance" before `get_balance`

**FR2: Voice-Formatted Responses**
- No raw JSON or technical data in responses
- Use natural, conversational language
- Summarize complex data clearly

**FR3: Error Handling**
- Clear error messages (no technical jargon)
- Example: "I'm having trouble retrieving that right now" instead of "HTTP 500 error"

### Non-Functional Requirements

**NFR1: Backward Compatibility**
- No breaking changes to MCP server
- Elicitation workflow unchanged
- PII masking continues to work

**NFR2: Simplicity**
- Minimal code changes
- No new dependencies
- Easy to demo and explain

---

## Implementation Plan

### Phase 1: Enhanced Instructions (Required)

**Task**: Update Agno agent instructions with voice UX guidelines

**Changes**:
- Update `agent.py` line 47-52 (agent instructions)
- Add acknowledgment examples for all tools
- Add response formatting guidelines

**Effort**: 1-2 hours

**Validation**: Test with each tool type, verify acknowledgments appear

### Phase 2: Response Formatter (Optional - If Needed)

**Task**: Add post-processing if instructions alone don't work well enough

**Changes**:
- Create `voice_ux/response_formatter.py`
- Update `llm_node()` to apply formatting
- Add formatters for each tool response type

**Effort**: 4-6 hours

**Validation**: Test all tool responses, verify natural language output

---

## Technical Details

### Architecture Validation

Based on code analysis of `livekit-voice-agent/agent.py`:

✅ **Streaming Architecture**: The `llm_node()` returns `AsyncIterable[str]`, supports our approach

✅ **Agno Integration**: Can enhance instructions or post-process responses

✅ **TTS Compatibility**: Cartesia TTS handles text streams naturally

✅ **PII Masking**: Existing `sanitize_text()` will work with formatted responses

✅ **No Breaking Changes**: All changes are in orchestrator, MCP/clients unchanged

### Current Flow

```
User speaks → STT → llm_node() → agent.arun() [BLOCKS 2-3s] → format → TTS → Audio
```

### Improved Flow

```
User speaks → STT → llm_node() → agent.arun() [generates acknowledgment + formatted response] → TTS → Audio
```

**Key Insight**: Instead of adding complexity, we teach the LLM (via instructions) to naturally provide better UX.

---

## Example Tool Responses

### get_balance

**Before**:
```
"balance_data: checking: 2500.00, savings: 3200.00, credit_card: -1240.50"
```

**After**:
```
"Let me check your balance. You have $2,500 in checking, $3,200 in savings, and a credit card balance of $1,240."
```

### get_user_details

**Before**:
```
"user_id: 12345, email: john@example.com, roles: ['customer'], permissions: ['read', 'transact', 'configure']"
```

**After**:
```
"Let me fetch your details. You're registered as John Smith with the email john@example.com. Your account has full customer access with transaction privileges."
```

### get_transactions

**Before**:
```
"transactions: [{date: 2025-11-18, amount: -45.20, merchant: 'Coffee Shop'}, {date: 2025-11-17, amount: -120.00, merchant: 'Gas Station'}, ...]"
```

**After**:
```
"Let me pull up your recent transactions. You had three transactions this week: a $45 purchase at the Coffee Shop, $120 at the Gas Station, and a $200 payment to your landlord."
```

---

## Files to Modify

### Required Changes

1. **`livekit-voice-agent/agent.py`** (lines 47-125)
   - Update Agno agent instructions with voice UX guidelines
   - Add acknowledgment patterns
   - Add response formatting examples

### Optional Changes (if Phase 2 needed)

2. **`livekit-voice-agent/voice_ux/response_formatter.py`** (NEW)
   - Create formatters for each tool response type
   - Convert JSON to conversational templates

3. **`livekit-voice-agent/agent.py`** (lines 189-204)
   - Apply formatting in `llm_node()` response stream

---

## Testing Approach

### Manual Testing

Test each tool with voice interaction:

1. **Balance Query**: "What's my balance?" → Verify acknowledgment + natural response
2. **User Details**: "What are my details?" → Verify acknowledgment + formatted output
3. **Transactions**: "Show my transactions" → Verify summary format
4. **Payments**: "Pay John $50" → Verify acknowledgment + elicitation flow works
5. **Error Case**: Disconnect MCP → Verify friendly error message

### Success Criteria

- ✅ Acknowledgments appear before tool calls (100% of time)
- ✅ No raw JSON in voice responses
- ✅ Responses sound natural when spoken aloud
- ✅ Elicitation workflow still works
- ✅ PII masking still applies

---

## Risks and Mitigations

| Risk | Mitigation |
|------|------------|
| LLM doesn't follow instructions consistently | Iterate on instruction wording; add post-processing if needed |
| Formatting breaks PII masking | Test with PII-heavy responses; masking runs after formatting |
| Changes break elicitation | Test payment flow; elicitation uses separate data channel |
| TTS mispronounces formatted text | Test various data patterns; adjust formatting templates |

---

## Out of Scope

For this hackathon POC, the following are explicitly OUT OF SCOPE:

- ❌ Metrics, dashboards, monitoring
- ❌ A/B testing frameworks
- ❌ Feature flags and gradual rollout
- ❌ Performance profiling and optimization
- ❌ Intent detection or prediction systems
- ❌ Configuration management systems
- ❌ Production deployment processes
- ❌ Load testing and scaling
- ❌ Detailed observability infrastructure

**Focus**: Core functionality that makes the voice UX significantly better for demos.

---

## Success Definition

This PRD is successful if:

1. **Demo Quality**: Voice assistant sounds natural and professional in demos
2. **No Awkward Silences**: Users always know what the agent is doing
3. **Easy to Understand**: Voice responses are clear without seeing data
4. **Works Reliably**: Improvements work for all tool types
5. **Simple Implementation**: Changes are straightforward and maintainable

---

## Change Log

| Change | Date | Version | Description | Author |
|--------|------|---------|-------------|--------|
| Initial creation | 2025-11-20 | v1.0 | Created hackathon-focused PRD for Voice UX enhancement | John (PM) |

---

**Status**: ✅ Ready for Implementation  
**Recommended Approach**: Start with Phase 1 (Enhanced Instructions), add Phase 2 only if needed  
**Estimated Effort**: 2-8 hours depending on approach  
**Demo Impact**: High - Every interaction will showcase improved UX
