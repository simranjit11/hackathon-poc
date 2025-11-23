"""
LiveKit Voice Agent - Quick Start
==================================
The simplest possible LiveKit voice agent to get you started.
Requires only OpenAI and Deepgram API keys.
"""

from typing import Any, AsyncIterable, Optional
from dotenv import load_dotenv
from livekit import agents
from livekit.agents import (
    AutoSubscribe,
    JobContext,
    JobProcess,
    WorkerOptions,
    cli,
    llm,
)
from livekit.agents import Agent, AgentSession, ModelSettings
from livekit.agents import log as agents_log
from jose import jwt

logger = agents_log.logger
from livekit.plugins import silero
from session_manager import get_session_manager
from mcp_client import get_mcp_client
from agno_tools import create_agno_mcp_tools
from agno.agent import Agent as AgnoAgent
from agno.models.openai import OpenAIChat
from ai_gateway import AIGateway
from pii_masking import sanitize_text, is_pii_masking_enabled
from elicitation_manager import get_elicitation_manager
from elicitation_response_handler import get_response_handler
from agno_redis_storage import get_agno_storage

from datetime import datetime, timedelta, timezone
import os
import json

# Load environment variables
load_dotenv()



class Assistant(Agent):
    """Banking voice assistant with comprehensive financial services."""

    def __init__(self):
        super().__init__(
            instructions="""You are a helpful and professional banking voice assistant.
            You can help customers with account balances, payments, transfers, transaction history,
            loan inquiries, and setting up payment reminders. Keep responses clear and professional."""
        )

        # MCP client for calling banking tools
        self.mcp_client = get_mcp_client()
        
        # Store user_id, email, and session_id for MCP calls
        # These will be set when the agent session starts
        self.user_id: Optional[str] = None
        self.email: Optional[str] = None
        self.session_id: Optional[str] = None
        
        # Agno agent will be initialized when user context is available
        self.agno_agent: Optional[AgnoAgent] = None
        
        # Room reference for sending data channel messages (elicitations)
        self.room: Optional[Any] = None
        
        # Log PII masking status
        if is_pii_masking_enabled():
            logger.info("🛡️ PII masking is ENABLED")
        else:
            logger.info("ℹ️ PII masking is DISABLED (set ENABLE_PII_MASKING=true to enable)")
    
    async def _initialize_agno_agent(self):
        """Initialize Agno agent with MCP server tools when user context is available."""
        if self.agno_agent is None:
            if not self.user_id or not self.session_id:
                logger.warning("Cannot initialize Agno agent: user_id or session_id not set")
                logger.warning(f"user_id={self.user_id}, session_id={self.session_id}")
                return
            
            # Create MCP tools wrapper
            mcp_tools_wrapper = create_agno_mcp_tools(
                self.user_id, 
                self.session_id,
            )
            
            # Get list of Function objects (these use our HTTP client with JWT)
            mcp_tools = mcp_tools_wrapper.get_tools()
            # Get model ID from environment or use default (gpt-4.1-mini for gateway)
            model_id = os.getenv("AI_MODEL_ID", "gpt-4.1-mini")
            
            # Try to use AI Gateway if configured, otherwise fall back to OpenAI
            try:
                # Use AI Gateway with proper URL structure and headers
                # agent_id is None, so AIGateway will use hardcoded constant UUID
                model = AIGateway(model_id=model_id)
            except ValueError as e:
                # AI Gateway not configured, fall back to OpenAI
                logger.warning(f"AI Gateway not configured ({e}), falling back to OpenAI")
                openai_api_key = os.getenv("OPENAI_API_KEY")
                if not openai_api_key:
                    raise ValueError("Neither AI Gateway nor OPENAI_API_KEY is configured")
                
                model = OpenAIChat(
                    id=model_id,
                    name=os.getenv("AI_MODEL_NAME", "GPT-4.1 Mini"),
                    api_key=openai_api_key,
                )
            
            # Get Redis database for session persistence
            agno_storage = get_agno_storage()
            db = agno_storage.get_db()
            
            # Initialize Agno agent with model (via AI Gateway or OpenAI) and MCP tools
            # Configure with Redis database for conversation memory
            # Based on Agno docs: https://docs.agno.com/concepts/agents/sessions
            self.agno_agent = AgnoAgent(
                name="banking_assistant",
                model=model,
                tools=mcp_tools,  # List of Function objects that call MCP server via HTTP with JWT
                instructions="""You are a helpful and professional banking voice assistant.

IMPORTANT: You MUST use the available tools to perform banking operations. Do not make up or guess information.

CRITICAL: TOOL CALL ANNOUNCEMENTS
- ALWAYS announce what you're about to do BEFORE calling any tool
- Examples:
  * Before calling get_transactions: "Hey, I'll check your transaction history. Give me a moment."
  * Before calling get_balance: "Let me check your account balance for you."
  * Before calling get_loans: "I'll look up your loan information right away."
  * Before calling get_transfer_contacts: "Let me pull up your saved contacts."
- Speak naturally and conversationally, then call the tool
- This helps users understand what's happening and reduces perceived wait time

PAYMENT COMPLETION AWARENESS:
- When a payment is confirmed and completed, you will receive a notification about it
- ALWAYS remember completed payments - they are stored in your conversation history
- If a user asks about a recent payment or transaction, check your conversation history first
- You will know about payments that were just completed because they are added to your memory
- When discussing completed payments, reference the confirmation number and details from your memory

FOR INITIAL GREETING (when user hasn't spoken yet):
- If this is the first interaction and you need to greet the user, FIRST call the get_user_details tool to get the user's name
- Then greet the user by name professionally (e.g., "Hello [name], how can I help you with your banking needs today?")
- If get_user_details fails, greet generically and ask how you can help

CRITICAL FOR WRITE OPERATIONS (create_reminder, update_reminder, delete_reminder, make_payment):
- These operations require multiple pieces of information
- If the user doesn't provide all required information, ASK for it before calling the tool
- For create_reminder, you need: scheduled_date, amount, recipient, and account_id
- For update_reminder, you need: reminder_id (string) and at least one field to update (scheduled_date, amount, recipient, description, account_id, or is_completed)
- For delete_reminder, you need: reminder_id (string)
- For make_payment, you need: to_account (string), amount (number), and optionally description (string)
- If account_id is missing for create_reminder, first call get_balance to get available accounts, then ask the user which account to use
- Collect ALL required information through conversation before calling the tool
- Once you have all required information, call the tool with primitive values (strings, numbers), NOT objects

DATE HANDLING (CRITICAL):
- When users provide dates/times in natural language (e.g., "December 20th at 10 AM", "tomorrow at 2pm", "next Friday at 3:30 PM"), you MUST automatically convert them to ISO 8601 format (e.g., "2025-12-20T10:00:00Z") before calling tools
- NEVER ask users to provide dates in ISO 8601 format - handle the conversion automatically
- Use the current date/time as reference when converting relative dates (e.g., "tomorrow", "next week")
- Always include timezone (use UTC/Z for consistency) when converting dates
- Examples:
  * "December 20th at 10 AM" → "2025-12-20T10:00:00Z"
  * "tomorrow at 2pm" → Calculate tomorrow's date and convert to "2025-12-23T14:00:00Z" (example)
  * "next Friday at 3:30 PM" → Calculate next Friday and convert to ISO 8601

DATE FORMATTING IN RESPONSES (CRITICAL):
- ALWAYS format dates in human-readable format when speaking to users
- NEVER read dates in raw format (e.g., "2025-11-25", "25/11/25", "2025-11-25T10:30:00Z")
- Convert dates to natural format: "November 25, 2025" or "Nov 25, 2025"
- For times, use: "November 25, 2025 at 10:30 AM" or "Nov 25, 2025 at 2:30 PM"
- Examples of date conversion:
  * "2025-11-25" → "November 25, 2025" or "Nov 25, 2025"
  * "2025-11-25T14:30:00Z" → "November 25, 2025 at 2:30 PM"
  * "2025-12-20T10:00:00Z" → "December 20, 2025 at 10:00 AM"
- When reading transaction dates, loan payment dates, reminder dates, etc., ALWAYS convert to human-readable format
- Use relative time when appropriate (e.g., "yesterday", "3 days ago", "next week") based on current date

CURRENT DATE/TIME AWARENESS:
- When you need to know the current date/time for context (e.g., to calculate relative dates, determine if something is overdue, etc.), call the get_current_date_time tool
- Use current date/time to provide context in responses (e.g., "Your next payment is due in 5 days" instead of just "Your next payment is on December 28")
- When reading transaction history, use current date to provide relative context (e.g., "3 days ago" instead of just the date)

When a user asks about:
- Account balances → Use the get_balance tool
- Transaction history → Use the get_transactions tool (ALWAYS format dates in human-readable format when reading results)
- Loans → Use the get_loans tool (ALWAYS format payment dates in human-readable format, use get_current_date_time to provide relative context)
- Credit limits → Use the get_credit_limit tool
- Interest rates → Use the get_interest_rates tool
- User profile/details → Use the get_user_details tool
- Current date/time → Use the get_current_date_time tool (call this when you need current date context for relative dates)
- Making payments → Use the initiate_payment tool (collect from_account, to_account, amount first; description optional)
- Creating reminders → Use the create_reminder tool (collect scheduled_date, amount, recipient, account_id first)
- Getting reminders → Use the get_reminders tool (optional filters: is_completed, scheduled_date_from, scheduled_date_to; ALWAYS format dates in human-readable format)
- Updating reminders → Use the update_reminder tool (requires reminder_id and fields to update)
- Deleting reminders → Use the delete_reminder tool (requires reminder_id)

RESPONSE FORMATTING FOR READ OPERATIONS:
- When reading transactions: 
  * Format dates as "November 25, 2025" or "Nov 25, 2025"
  * Use relative time when helpful (e.g., "3 days ago", "last week")
  * Example: Instead of "Transaction on 2025-11-20", say "Transaction on November 20, 2025" or "Transaction from 3 days ago"
  * Call get_current_date_time if you need to calculate relative dates
  
- When reading loans:
  * Format next payment date as "December 28, 2025" 
  * ALWAYS call get_current_date_time first to provide relative context
  * Example: "Your next payment of $500 is due on December 28, 2025, which is in 5 days"
  * Instead of "next_payment_date: 2025-12-28", say "December 28, 2025" or "Dec 28, 2025"
  
- When reading reminders:
  * Format scheduled dates as "January 15, 2026" or "Jan 15, 2026"
  * Call get_current_date_time to provide relative context
  * Example: "You have a reminder scheduled for January 15, 2026, which is in 3 weeks"
  
- When reading contacts/beneficiaries:
  * Format any dates in human-readable format
  * No need to call get_current_date_time unless providing relative context
  
- Date conversion rules:
  * "2025-11-25" → "November 25, 2025" or "Nov 25, 2025"
  * "2025-11-25T14:30:00Z" → "November 25, 2025 at 2:30 PM"
  * "2025-12-20T10:00:00Z" → "December 20, 2025 at 10:00 AM"
  * Always convert ISO dates (YYYY-MM-DD or YYYY-MM-DDTHH:MM:SSZ) to human-readable format before speaking
  * NEVER read raw date formats like "25/11/25", "2025-11-25", or ISO timestamps directly
  
- Current date/time usage:
  * Call get_current_date_time tool when you need to:
    - Calculate relative dates (e.g., "3 days ago", "in 5 days")
    - Determine if something is overdue or upcoming
    - Provide context about when something happened relative to now
  * Use it BEFORE reading transactions, loans, or reminders to provide better context

WORKFLOW FOR WRITE OPERATIONS:
1. User expresses intent (e.g., "create a reminder", "update my reminder", "delete a reminder")
2. Identify what information is missing
3. Ask user for missing information one piece at a time
4. If account_id is needed for create_reminder, call get_balance first to show available accounts
5. If reminder_id is needed for update/delete, call get_reminders first to show available reminders
6. Once ALL required information is collected, call the tool
7. Confirm the operation was successful

PAYMENT WORKFLOW (CRITICAL - FOLLOW THESE STEPS):
When a user requests a payment/transfer (e.g., "Send $100 to John", "Pay Bob $50"):

1. FIRST: Call get_transfer_contacts to get the list of saved beneficiaries
2. THEN: Match the recipient name mentioned by the user against the contact list:
   - Look for matches by nickname, fullName, or any part of the name
   - If you find EXACTLY ONE match → Proceed to step 3
   - If you find MULTIPLE matches (e.g., "John" matches "John Smith" and "John Doe"):
     * List all matching contacts with their full names
     * Ask user: "I found multiple contacts named John: John Smith and John Doe. Which one would you like to pay?"
     * Wait for user clarification, then proceed to step 3
   - If you find NO matches:
     * Inform user: "I couldn't find a contact named [name]. Would you like to add them first or provide their account details?"
     * Do NOT proceed with payment

3. CHECK if user specified source account:
   - If user said "from checking" or "from savings" → Use that account
   - If user did NOT specify → Call get_balance to show available accounts and ask: "Would you like to pay from your checking or savings account?"
   - Wait for user to specify the account

4. FINALLY: Call initiate_payment with:
   - from_account: REQUIRED - The account type user selected ('checking' or 'savings')
   - to_account: Use the paymentAddress (UPI ID/account number) from the matched contact - NEVER use the name
   - amount: The amount user specified
   - description: Optional - can include recipient's full name for clarity

EXAMPLE:
User: "Send $100 to John from my checking account"
Step 1: get_transfer_contacts() → Returns [{"nickname":"John","fullName":"John Jacob","paymentAddress":"john@okicici.com","paymentType":"upi"}]
Step 2: Found 1 match for "John"
Step 3: User specified "checking account"
Step 4: initiate_payment(from_account="checking", to_account="john@okicici.com", amount=100, description="Transfer to John Jacob")

Always call the appropriate tool first, then use the tool's response to answer the user's question. Never provide information without calling the tools first.

Keep responses clear, professional, and based on actual tool responses.""",
                markdown=True,
                # Session and database configuration for conversation memory
                db=db,  # Redis database for persistent memory
                session_id=self.session_id,  # Use room_name as session_id to maintain context across the conversation
                user_id=self.user_id,  # Track sessions per user
                add_history_to_context=True,  # Include conversation history in context
                num_history_runs=10,  # Keep last 10 exchanges in memory
                # Add session state for maintaining conversation context
                add_session_state_to_context=True,
                session_state={},  # Initialize empty state that will be persisted
            )
    
    async def llm_node(
        self, 
        chat_ctx: llm.ChatContext, 
        tools: list[llm.FunctionTool], 
        model_settings: ModelSettings
    ):
        """
        Intercepts User Input -> LLM using Agno framework.
        Optionally sanitizes the chat context so the LLM never sees the raw PII (if enabled).
        Agno automatically handles tool calling based on tool definitions.
        """
        # Ensure Agno agent is initialized (async)
        await self._initialize_agno_agent()
        
        if not self.agno_agent:
            # Fallback to default if Agno not initialized
            logger.warning("Agno agent not initialized, falling back to default LLM")
            logger.warning(f"Initialization check: user_id={self.user_id}, session_id={self.session_id}, email={self.email}")
            return super().llm_node(chat_ctx, tools, model_settings)
        
        # Extract user message from LiveKit context
        user_message = None
        items = chat_ctx.items
        if items:
            # Find the last user message
            for item in reversed(items):
                if hasattr(item, 'type') and item.type == 'message' and hasattr(item, 'role'):
                    if item.role == "user":
                        user_message = item.text_content
                        if user_message:
                            # Optionally sanitize PII before sending to Agno (if enabled)
                            sanitized_message = sanitize_text(user_message)
                            user_message = sanitized_message
                        break
        
        # Check if this is a generate_reply call (instructions provided via system/assistant message)
        # generate_reply() may pass instructions as system messages or assistant messages
        if not user_message and items:
            for item in reversed(items):
                if hasattr(item, 'type') and item.type == 'message' and hasattr(item, 'role'):
                    if item.role == "system" or item.role == "assistant":
                        # Check if this is an instruction for generate_reply
                        instruction_text = getattr(item, 'text_content', None) or getattr(item, 'content', None)
                        if instruction_text:
                            # Check for common instruction patterns
                            if any(keyword in instruction_text for keyword in ["SYSTEM:", "Inform the user", "Great news", "Tell the user", "Acknowledge"]):
                                user_message = instruction_text
                                logger.info(f"Detected generate_reply instruction: {instruction_text[:150]}...")
                                break
                            # Also check if it's a direct instruction (not a user message)
                            elif len(instruction_text) > 20 and ("payment" in instruction_text.lower() or "transaction" in instruction_text.lower()):
                                user_message = instruction_text
                                logger.info(f"Detected potential instruction message: {instruction_text[:150]}...")
                                break
        
        # If no user message, this might be an initial greeting or generate_reply call
        # Still use Agno agent so it can call get_user_details for personalized greeting
        if not user_message:
            user_message = ""  # Empty message, but we'll still call Agno
            logger.debug("No user message found, using empty string for Agno")
        
        # Run Agno agent with user message
        # Agno will automatically call MCP tools as needed
        try:
            # Log that we're about to call Agno
            logger.info(f"Calling Agno agent with message: {user_message[:100]}...")
            
            # Run Agno agent - it should automatically call tools
            # Note: Since our tools are async, we must use arun() instead of run()
            logger.info(f"Running Agno agent.arun() with message: {user_message[:50]}...")
            response = await self.agno_agent.arun(user_message)
            
            # Log the response
            logger.info(f"Agno agent responded. Response type: {type(response)}")
            logger.info(f"Response attributes: {dir(response)}")
            
            if hasattr(response, 'content'):
                logger.info(f"Response content length: {len(str(response.content))}")
                logger.info(f"Response content (first 200 chars): {str(response.content)[:200]}")
            if hasattr(response, 'messages'):
                logger.info(f"Response messages: {len(response.messages) if response.messages else 0}")
            
            # Check if any tool calls resulted in elicitation
            elicitation_response = None
            
            # Try different attributes where tool results might be stored
            tools_attr = None
            if hasattr(response, 'tools'):
                tools_attr = response.tools
                logger.info(f"Found 'tools' attribute with {len(tools_attr) if tools_attr else 0} items")
            elif hasattr(response, 'tool_calls'):
                tools_attr = response.tool_calls
                logger.info(f"Found 'tool_calls' attribute with {len(tools_attr) if tools_attr else 0} items")
            elif hasattr(response, 'run_response') and hasattr(response.run_response, 'tools'):
                tools_attr = response.run_response.tools
                logger.info(f"Found 'run_response.tools' attribute with {len(tools_attr) if tools_attr else 0} items")
            
            if tools_attr:
                logger.info(f"Checking {len(tools_attr)} tool results for elicitation")
                for idx, tool_result in enumerate(tools_attr):
                    logger.info(f"Tool result {idx}: type={type(tool_result)}, attrs={dir(tool_result)}")
                    
                    # Try to get the result from different possible attributes
                    result = None
                    if hasattr(tool_result, 'result'):
                        result = tool_result.result
                    elif hasattr(tool_result, 'output'):
                        result = tool_result.output
                    elif isinstance(tool_result, dict):
                        result = tool_result
                    
                    if result:
                        logger.info(f"Tool result {idx} data type: {type(result)}")
                        logger.info(f"Tool result {idx} data (first 200 chars): {str(result)[:200]}")
                        
                        # Parse the result - it might be wrapped in MCP format or be a direct dict
                        parsed_result = None
                        
                        # First, if result is a string, try to evaluate it as a Python literal (dict/list)
                        if isinstance(result, str):
                            # Try parsing as JSON first
                            try:
                                result = json.loads(result)
                                logger.info(f"Parsed result from JSON string to: {type(result)}")
                            except (json.JSONDecodeError, TypeError):
                                # Try evaluating as Python literal (for string repr of dict)
                                try:
                                    import ast
                                    result = ast.literal_eval(result)
                                    logger.info(f"Evaluated result from Python literal to: {type(result)}")
                                except (ValueError, SyntaxError):
                                    logger.debug(f"Could not parse string as JSON or Python literal: {result[:100]}")
                        
                        # Now handle dict results
                        if isinstance(result, dict):
                            # Check if it's wrapped in MCP content format
                            if 'content' in result and isinstance(result['content'], list):
                                # Extract text from first content item
                                for content_item in result['content']:
                                    if isinstance(content_item, dict) and content_item.get('type') == 'text':
                                        text_value = content_item.get('text', '')
                                        # Try to parse as JSON
                                        try:
                                            parsed_result = json.loads(text_value)
                                            logger.info(f"✅ Parsed JSON from MCP content.text: {type(parsed_result)}")
                                            break
                                        except (json.JSONDecodeError, TypeError):
                                            logger.debug(f"Could not parse text as JSON: {text_value[:100]}")
                            else:
                                # Direct dict, use as-is
                                parsed_result = result
                                logger.info(f"Using result dict as-is")
                        
                        # Check if the parsed result is an elicitation response
                        if isinstance(parsed_result, dict) and parsed_result.get('elicitation_id'):
                            logger.info(f"✅ Found elicitation in tool result: {parsed_result.get('elicitation_id')}")
                            elicitation_response = parsed_result
                            
                            # CRITICAL: Store elicitation state in Redis
                            # This was missing - the orchestrator must save elicitation to Redis
                            # so it can be retrieved when user responds
                            try:
                                from schemas.elicitation import ElicitationSchema
                                elicitation_manager = get_elicitation_manager()
                                
                                schema_dict = elicitation_response.get('schema', {})
                                elicitation_schema = ElicitationSchema(**schema_dict)
                                
                                elicitation_manager.create_elicitation(
                                    tool_call_id=elicitation_response.get('tool_call_id', ''),
                                    mcp_endpoint='initiate_payment',
                                    user_id=self.user_id,
                                    session_id=self.session_id,
                                    room_name=self.session_id,  # Using session_id as room_name
                                    schema=elicitation_schema,
                                    suspended_tool_arguments=elicitation_response.get('suspended_arguments', {}),
                                    timeout_seconds=schema_dict.get('timeout_seconds', 300)
                                )
                                logger.info(f"✅ Saved elicitation {elicitation_response.get('elicitation_id')} to Redis")
                            except Exception as e:
                                logger.error(f"❌ Failed to save elicitation to Redis: {e}", exc_info=True)
                            
                            break
            else:
                logger.warning("No tool results found in response")
            
            # If there's an elicitation, send it to the UI via data channel
            if elicitation_response:
                logger.info(f"Sending elicitation {elicitation_response.get('elicitation_id')} to UI")
                
                # Send elicitation to UI via data channel
                if self.room:
                    try:
                        # Wrap the elicitation in the format expected by the frontend
                        # Frontend expects: { type: "elicitation", elicitation_id, tool_call_id, schema }
                        message = {
                            "type": "elicitation",
                            "elicitation_id": elicitation_response.get('elicitation_id'),
                            "tool_call_id": elicitation_response.get('tool_call_id'),
                            "schema": elicitation_response.get('schema', {}),
                        }
                        elicitation_json = json.dumps(message)
                        elicitation_bytes = elicitation_json.encode('utf-8')
                        await self.room.local_participant.publish_data(elicitation_bytes)
                        logger.info(f"Successfully sent elicitation {elicitation_response.get('elicitation_id')} to UI with type='elicitation'")
                    except Exception as e:
                        logger.error(f"Failed to send elicitation to UI: {e}")
                else:
                    logger.warning("Room not available, cannot send elicitation to UI")
                
                # Return a voice response telling user to check their device
                response_text = "I've sent a payment confirmation request to your device. Please review the details and enter the OTP code to complete the transaction."
            else:
                # Convert Agno response to LiveKit streaming format
                # Agno returns a RunResponse object with content
                response_text = response.content if hasattr(response, 'content') else str(response)
            
            # Stream the response back as async generator
            async def agno_response_stream():
                # Yield response in chunks to simulate streaming
                chunk_size = 50
                for i in range(0, len(response_text), chunk_size):
                    chunk = response_text[i:i + chunk_size]
                    # Optionally sanitize output before streaming (if enabled)
                    sanitized_chunk = sanitize_text(chunk)
                    yield sanitized_chunk
            
            # Return the stream
            return agno_response_stream()
            
        except Exception as e:
            logger.error(f"Error in Agno LLM node: {e}")
            # Fallback to default on error
            return super().llm_node(chat_ctx, tools, model_settings)
    
    def tts_node(self, text: AsyncIterable[str], model_settings: ModelSettings):
        """
        Intercepts LLM Output -> TTS.
        Optionally sanitizes the stream before the agent speaks it (if enabled).
        """
        
        # We define a generator to wrap the incoming text stream
        async def safe_text_stream():
            async for chunk in text:
                # Note: Running Presidio on small chunks (tokens) is inaccurate.
                # Ideally, you should buffer by sentence. 
                # For this sample, we assume 'chunk' is substantial or we accept partial redaction risks.
                # LiveKit's LLM stream usually yields chunks; a buffer might be needed for production accuracy.
                sanitized_chunk = sanitize_text(chunk)
                yield sanitized_chunk

        # Pass the safe stream to the original TTS node logic
        return super().tts_node(safe_text_stream(), model_settings)
        

async def entrypoint(ctx: agents.JobContext):
    """
    Entrypoint for LiveKit voice agent.
    Initializes session with user identity from participant metadata.
    """
    room = ctx.room
    room_name = room.name

    # Extract user identity from participant metadata
    user_id = None
    email = None
    roles = ["customer"]
    permissions = ["read"]
    platform = "web"

    # Connect to the room first
    logger.info(f"Connecting to room {room_name}")
    await ctx.connect(auto_subscribe=AutoSubscribe.AUDIO_ONLY)
    logger.info(f"Connected to room {room_name}")

    logger.info(f"Waiting for participant to join room {room_name}...")
    participant = await ctx.wait_for_participant()
    logger.info(f"Participant joined: {participant.identity}, metadata: {participant.metadata}")

    # Check this specific participant (no need to loop over all if we waited for one)
    if participant:
        if participant.metadata:
            try:
                # Check if metadata is a string (not a MagicMock in console mode)
                if isinstance(participant.metadata, str):
                    metadata = json.loads(participant.metadata)
                    user_id = metadata.get("user_id")
                    email = metadata.get("email")
                    roles = metadata.get("roles", ["customer"])
                    permissions = metadata.get("permissions", ["read"])
                    # Determine platform from metadata or participant name
                    platform = metadata.get("platform", "web")
            except (json.JSONDecodeError, AttributeError, TypeError) as e:
                # If JSON parsing fails, check if it's a JWT token string
                if isinstance(participant.metadata, str) and (participant.metadata.startswith("eyJ") or "Bearer " in participant.metadata):
                    try:
                        # Clean up token if needed
                        token = participant.metadata.replace("Bearer ", "").strip()
                        # Decode without verification to extract claims
                        claims = jwt.get_unverified_claims(token)
                        
                        user_id = claims.get("user_id") or claims.get("sub")
                        email = claims.get("email")
                        roles = claims.get("roles", ["customer"])
                        permissions = claims.get("permissions", ["read"])
                    except Exception:
                        pass

    # If no metadata found, try to extract from participant identity
    # Fallback: use participant identity if it follows the pattern voice_assistant_user_{user_id}
    if not user_id and participant:
        identity = participant.identity
        # Check if identity is a string (not a MagicMock)
        if isinstance(identity, str) and identity.startswith("voice_assistant_user_"):
            user_id = identity.replace("voice_assistant_user_", "")
            # Use default values if metadata not available
            email = f"user_{user_id}@example.com"

    # Final fallback: use environment variable or default for console mode
    if not user_id:
        user_id = os.getenv("DEFAULT_USER_ID", "12345")
        email = f"user_{user_id}@example.com"
        logger.info(f"Using default user_id from environment: {user_id}")

    # Initialize session in Redis if user_id is available
    session_manager = get_session_manager()
    if user_id:
        try:
            session_manager.create_session(
                user_id=user_id,
                email=email or f"user_{user_id}@example.com",
                roles=roles if isinstance(roles, list) else [roles],
                permissions=permissions if isinstance(permissions, list) else [permissions],
                room_name=room_name,
                platform=platform,
            )
        except Exception:
            pass

    # Create agent instance
    assistant = Assistant()
    
    # Set user context for MCP calls
    if user_id:
        assistant.user_id = user_id
        assistant.email = email or f"user_{user_id}@example.com"
        assistant.session_id = room_name
    
    # Store room reference for data channel access (elicitations)
    assistant.room = room
    logger.info(f"Set agent context: user_id={user_id}, email={assistant.email}, session_id={room_name}")

    # Create agent session
    # Note: Using VAD (Voice Activity Detection) for turn detection instead of MultilingualModel
    # VAD handles voice activity without requiring model downloads
    # Get model ID for LiveKit session (fallback to default if not set)
    # Note: LiveKit uses a different format, but we'll use the same model ID
    livekit_model_id = os.getenv("AI_MODEL_ID", "gpt-4.1-mini")
    
    agent_session = AgentSession(
        stt="assemblyai/universal-streaming:en",
        llm=f"openai/{livekit_model_id}",
        tts="cartesia/sonic-3:a167e0f3-df7e-4d52-a9c3-f949145efdab",  # Male voice
        vad=silero.VAD.load(),
        # turn_detection removed - VAD handles voice activity detection without model downloads
    )

    # Initialize elicitation handler
    elicitation_manager = get_elicitation_manager()
    response_handler = get_response_handler()
    
    # Setup data channel listener for elicitation responses
    @room.on("data_received")
    def on_data_received(data_packet):
        """Handle data channel messages from client (elicitation responses)."""
        try:
            # Decode the data
            payload_bytes = bytes(data_packet.data)
            payload_str = payload_bytes.decode('utf-8')
            payload = json.loads(payload_str)
            
            # Handle elicitation response
            if payload.get("type") == "elicitation_response":
                elicitation_id = payload.get("elicitation_id")
                user_input = payload.get("user_input")
                biometric_token = payload.get("biometric_token")
                
                # Handle response asynchronously
                async def handle_async():
                    try:
                        result = await response_handler.handle_response(
                            elicitation_id=elicitation_id,
                            user_input=user_input,
                            biometric_token=biometric_token
                        )
                        
                        # Send result back to client
                        result_json = json.dumps(result)
                        result_bytes = result_json.encode('utf-8')
                        await room.local_participant.publish_data(result_bytes)
                        
                        # If successful, narrate confirmation to user
                        if result.get('status') == 'completed':
                            payment_result = result.get('payment_result', {})
                            confirmation = payment_result.get('confirmation_number', 'Unknown')
                            amount = payment_result.get('amount', 0)
                            from_account = payment_result.get('from_account', 'your account')
                            to_account = payment_result.get('to_account', 'the recipient')
                            
                            # Format amount nicely
                            amount_str = f"${amount:.2f}" if isinstance(amount, (int, float)) else str(amount)
                            
                            logger.info(
                                f"✅ Payment completed: {amount_str} from {from_account} to {to_account}, "
                                f"confirmation: {confirmation}"
                            )
                            
                            # Update session state with payment completion
                            try:
                                session_manager = get_session_manager()
                                if assistant.user_id and assistant.session_id:
                                    # Store payment completion in session
                                    session_manager.update_session(
                                        assistant.session_id,
                                        assistant.user_id,
                                        {
                                            "last_payment_confirmation": confirmation,
                                            "last_payment_amount": amount_str,
                                            "last_payment_from": from_account,
                                            "last_payment_to": to_account,
                                            "last_payment_completed_at": datetime.utcnow().isoformat()
                                        }
                                    )
                                    logger.info(f"Updated session state with payment completion: {confirmation}")
                            except Exception as e:
                                logger.error(f"Error updating session state: {e}", exc_info=True)
                            
                            # Generate voice response by simulating a user message
                            # This is more reliable than using generate_reply with instructions
                            if assistant.agno_agent:
                                try:
                                    logger.info("Processing payment completion notification...")
                                    
                                    # Create a user message that simulates the user confirming the payment
                                    # This will go through the normal llm_node flow and generate a natural response
                                    user_confirmation_message = (
                                        f"I've confirmed the payment of {amount_str} from {from_account} "
                                        f"to {to_account}. The confirmation number is {confirmation}."
                                    )
                                    
                                    logger.info(f"Simulating user message to trigger agent response: {user_confirmation_message[:100]}...")
                                    
                                    # Use generate_reply with user_input to simulate a user message
                                    # This will go through llm_node normally and trigger TTS
                                    await agent_session.generate_reply(
                                        user_input=user_confirmation_message
                                    )
                                    
                                    logger.info("Voice response generated for payment completion")
                                    
                                except Exception as e:
                                    logger.error(f"Error processing payment completion: {e}", exc_info=True, stack_info=True)
                                    # Fallback: try with a simpler message
                                    try:
                                        logger.info("Attempting fallback voice response...")
                                        fallback_message = (
                                            f"Payment of {amount_str} confirmed. Confirmation number {confirmation}."
                                        )
                                        await agent_session.generate_reply(
                                            user_input=fallback_message
                                        )
                                        logger.info("Fallback voice response generated")
                                    except Exception as fallback_error:
                                        logger.error(f"Fallback generate_reply also failed: {fallback_error}", exc_info=True, stack_info=True)
                                        # Last resort: log the error but don't crash
                                        logger.error("Could not generate voice response for payment completion")
                            else:
                                logger.warning("Agno agent not initialized, using fallback notification")
                                await agent_session.generate_reply(
                                    user_input=(
                                        f"Payment of {amount_str} confirmed. Confirmation number {confirmation}."
                                    )
                                )
                        else:
                            error = result.get('error', 'Unknown error')
                            
                            # Add error to Agno agent's memory
                            if assistant.agno_agent:
                                try:
                                    await assistant.agno_agent.arun(
                                        f"SYSTEM UPDATE: The payment confirmation failed with error: {error}. Inform the user and offer to help retry."
                                    )
                                except Exception as e:
                                    logger.error(f"Error updating Agno agent memory: {e}")
                                    await agent_session.generate_reply(
                                        user_input=f"Payment confirmation failed: {error}"
                                    )
                            else:
                                await agent_session.generate_reply(
                                    user_input=f"Payment confirmation failed: {error}"
                                )
                            
                    except Exception as e:
                        logger.error(f"[Elicitation] Error handling response: {e}", exc_info=True)
                
                # Schedule the async handler
                import asyncio
                asyncio.create_task(handle_async())
                
        except Exception as e:
            logger.error(f"[DataChannel] Error processing data: {e}", exc_info=True)

    # Start the session
    await agent_session.start(
        room=room,
        agent=assistant
    )

    # Generate initial greeting
    # Note: llm_node will detect this is an initial greeting (no user message)
    # and automatically inject user context by calling get_user_details
    await agent_session.generate_reply(
        instructions="Greet the user professionally as a banking assistant and ask how you can help with their banking needs today."
    )

if __name__ == "__main__":
    # Run the agent
    agents.cli.run_app(agents.WorkerOptions(entrypoint_fnc=entrypoint))
