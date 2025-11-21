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
            loan inquiries, and setting up alerts. Keep responses clear and professional."""
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
        
        # Log PII masking status
        if is_pii_masking_enabled():
            logger.info("🛡️ PII masking is ENABLED")
        else:
            logger.info("ℹ️ PII masking is DISABLED (set ENABLE_PII_MASKING=true to enable)")
    
    async def _initialize_agno_agent(self):
        """Initialize Agno agent with MCP server tools when user context is available."""
        if self.agno_agent is None and self.user_id and self.session_id:
            # Create MCP tools wrapper
            mcp_tools_wrapper = create_agno_mcp_tools(
                self.user_id, 
                self.session_id,
                self.email
            )
            
            # Get list of Function objects (these use our HTTP client with JWT)
            mcp_tools = mcp_tools_wrapper.get_tools()
            logger.info(f"Created {len(mcp_tools)} MCP tools for Agno")
            
            # Get model ID from environment or use default (gpt-4.1-mini for gateway)
            model_id = os.getenv("AI_MODEL_ID", "gpt-4.1-mini")
            
            # Try to use AI Gateway if configured, otherwise fall back to OpenAI
            try:
                # Use AI Gateway with proper URL structure and headers
                # agent_id is None, so AIGateway will use hardcoded constant UUID
                model = AIGateway(model_id=model_id)
                logger.info(f"Using AI Gateway with model: {model_id}")
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
                logger.info(f"Using OpenAI API directly with model: {model_id}")
            
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

When a user asks about:
- Account balances → Use the get_balance tool
- Transaction history → Use the get_transactions tool
- Loans → Use the get_loans tool
- Credit limits → Use the get_credit_limit tool
- Alerts → Use the get_alerts tool
- Interest rates → Use the get_interest_rates tool
- User profile/details → Use the get_user_details tool
- Making payments/transfers → Use the initiate_payment tool (this will trigger OTP/confirmation elicitation)
- Setting alerts → Use the set_alert tool

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
            logger.info(f"Initialized Agno agent with Redis storage and session context for user_id: {self.user_id}, session_id: {self.session_id}")
    
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
                            if sanitized_message != user_message:
                                logger.info(f"Sanitized User Input before Agno: {user_message[:50]}... -> {sanitized_message[:50]}...")
                            user_message = sanitized_message
                        break
                            
        if not user_message:
            # No user message, return default behavior
            return super().llm_node(chat_ctx, tools, model_settings)
        
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
            if hasattr(response, 'content'):
                logger.info(f"Response content length: {len(str(response.content))}")
            if hasattr(response, 'messages'):
                logger.info(f"Response messages: {len(response.messages) if response.messages else 0}")
            
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
        print(f"DEBUG: Participant Identity: {participant.identity}")
        print(f"DEBUG: Metadata type: {type(participant.metadata)}")
        print(f"DEBUG: Metadata content: {participant.metadata}")
        
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
                        
                        logger.info("Successfully extracted user identity from JWT in metadata")
                        user_id = claims.get("user_id") or claims.get("sub")
                        email = claims.get("email")
                        roles = claims.get("roles", ["customer"])
                        permissions = claims.get("permissions", ["read"])
                    except Exception as jwt_error:
                        logger.debug(f"Failed to parse metadata as JWT: {jwt_error}")

                logger.debug(f"Error parsing participant metadata: {e}")

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
            session_key = session_manager.create_session(
                user_id=user_id,
                email=email or f"user_{user_id}@example.com",
                roles=roles if isinstance(roles, list) else [roles],
                permissions=permissions if isinstance(permissions, list) else [permissions],
                room_name=room_name,
                platform=platform,
            )
            print(f"Session initialized: {session_key}")
            print(f"User: {user_id} ({email}), Roles: {roles}, Permissions: {permissions}")
        except Exception as e:
            print(f"Warning: Could not create session: {e}")
            print("Continuing without session management...")
    else:
        print("Warning: No user_id found in participant metadata. Session not created.")

    # Create agent instance
    assistant = Assistant()
    
    # Set user context for MCP calls
    if user_id:
        assistant.user_id = user_id
        assistant.email = email or f"user_{user_id}@example.com"
        assistant.session_id = room_name
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
            
            logger.info(f"[DataChannel] Received message type: {payload.get('type')}")
            
            # Handle elicitation response
            if payload.get("type") == "elicitation_response":
                elicitation_id = payload.get("elicitation_id")
                user_input = payload.get("user_input")
                biometric_token = payload.get("biometric_token")
                
                logger.info(f"[Elicitation] Processing response for {elicitation_id}")
                
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
                            
                            await agent_session.generate_reply(
                                instructions=f"Inform the user that their payment of {amount} has been completed successfully with confirmation number {confirmation}."
                            )
                        else:
                            error = result.get('error', 'Unknown error')
                            await agent_session.generate_reply(
                                instructions=f"Inform the user that their payment could not be completed: {error}"
                            )
                            
                    except Exception as e:
                        logger.error(f"[Elicitation] Error handling response: {e}", exc_info=True)
                
                # Schedule the async handler
                import asyncio
                asyncio.create_task(handle_async())
                
        except Exception as e:
            logger.error(f"[DataChannel] Error processing data: {e}", exc_info=True)
    
    logger.info("[DataChannel] Elicitation handler registered")

    # Start the session
    await agent_session.start(
        room=room,
        agent=assistant
    )

    # Generate initial greeting
    await agent_session.generate_reply(
        instructions="Greet the user professionally as a banking assistant and ask how you can help with their banking needs today."
    )

if __name__ == "__main__":
    # Run the agent
    agents.cli.run_app(agents.WorkerOptions(entrypoint_fnc=entrypoint))
