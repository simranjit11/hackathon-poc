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

logger = agents_log.logger
from livekit.plugins import silero
from session_manager import get_session_manager
from mcp_client import get_mcp_client
from agno_tools import create_agno_mcp_tools
from agno import Agent as AgnoAgent
from agno.models.openai import OpenAIChat

from datetime import datetime, timedelta, timezone
import os
import json

# Load environment variables
load_dotenv()

# JWT Token Generation
try:
    from jose import jwt
    JOSE_AVAILABLE = True
except ImportError:
    JOSE_AVAILABLE = False


class JWTAuthenticatedMCPServer(mcp.MCPServerHTTP):
    """
    MCP Server wrapper that adds JWT authentication via HTTP headers.
    
    JWT token is sent in the Authorization header as "Bearer <token>"
    and automatically included in all MCP tool calls.
    """
    
    def __init__(
        self,
        url: str,
        user_id: str,
        headers: dict[str, Any] | None = None,
        timeout: float = 5,
        sse_read_timeout: float = 60 * 5,
        client_session_timeout_seconds: float = 5,
    ) -> None:
        # Store configuration first
        self._user_id = user_id
        self._jwt_secret_key = os.getenv("MCP_JWT_SECRET_KEY", "your-secret-key-change-in-production")
        self._jwt_issuer = os.getenv("MCP_JWT_ISSUER", "orchestrator")
        self._jwt_algorithm = os.getenv("MCP_JWT_ALGORITHM", "HS256")
        
        # Generate JWT token
        jwt_token = self._generate_jwt_token(user_id)
        
        # Add JWT to headers (Authorization: Bearer <token>)
        auth_headers = headers.copy() if headers else {}
        auth_headers["Authorization"] = f"Bearer {jwt_token}"
        
        super().__init__(
            url=url,
            headers=auth_headers,
            timeout=timeout,
            sse_read_timeout=sse_read_timeout,
            client_session_timeout_seconds=client_session_timeout_seconds,
        )
    
    def _generate_jwt_token(self, user_id: str, scopes: list[str] = None) -> str:
        """Generate JWT token for MCP server authentication."""
        if not JOSE_AVAILABLE:
            raise RuntimeError("python-jose is required for JWT generation")
        
        if scopes is None:
            scopes = ["read"]
        
        now = datetime.now(timezone.utc)
        exp = now + timedelta(minutes=15)
        
        payload = {
            "iss": self._jwt_issuer,
            "sub": user_id,
            "scopes": scopes,
            "iat": int(now.timestamp()),
            "exp": int(exp.timestamp()),
            "jti": f"agent-{int(now.timestamp())}"
        }
        
        return jwt.encode(payload, self._jwt_secret_key, algorithm=self._jwt_algorithm)


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
        
        # Store user_id and session_id for MCP calls
        # These will be set when the agent session starts
        self.user_id: Optional[str] = None
        self.session_id: Optional[str] = None
        
        # Agno agent will be initialized when user context is available
        self.agno_agent: Optional[AgnoAgent] = None

    def _sanitize_text(self, text: str) -> str:
        """Helper to run Presidio Analyzer and Anonymizer on text."""
        if not text or text.strip() == "":
            return text
            
        # 1. Analyze (Detect PII)
        # Include OTP and other sensitive entities
        analyzer = get_analyzer()
        results = analyzer.analyze(
            text=text, 
            entities=["OTP", "PERSON", "EMAIL_ADDRESS", "PHONE_NUMBER", "CREDIT_CARD", "SSN", "IBAN_CODE", "US_DRIVER_LICENSE", "US_PASSPORT", "US_BANK_NUMBER"], 
            language='en'
        )
        
        # 2. Anonymize (Redact PII)
        # You can customize operators: "replace", "mask", "redact", "hash"
        anonymizer = get_anonymizer()
        anonymized_result = anonymizer.anonymize(
            text=text,
            analyzer_results=results,
            operators={"DEFAULT": OperatorConfig("replace", {"new_value": "[REDACTED]"})}
        )
        
        if len(results) > 0:
            logger.info(f"🛡️ Guardrail triggered. Redacted {len(results)} entities.")
            
        return anonymized_result.text
    
    def _initialize_agno_agent(self):
        """Initialize Agno agent with MCP server tools when user context is available."""
        if self.agno_agent is None and self.user_id and self.session_id:
            # Create MCP tools - Agno will automatically discover tools from MCP server
            mcp_tools = create_agno_mcp_tools(self.user_id, self.session_id)
            
            # Initialize Agno agent with OpenAI model and MCP tools
            # Agno automatically discovers and uses tools from MCP server
            self.agno_agent = AgnoAgent(
                name="banking_assistant",
                model=OpenAIChat(
                    id="gpt-4o-mini",
                    name="GPT-4o Mini",
                ),
                tools=[mcp_tools],  # MCP server tools are automatically discovered
                instructions="""You are a helpful and professional banking voice assistant.
                You can help customers with account balances, payments, transfers, transaction history,
                loan inquiries, and setting up alerts. Keep responses clear and professional.
                Use the available tools from the MCP server to perform banking operations automatically when needed.""",
                markdown=True,
            )
            logger.info(f"Initialized Agno agent with MCP server tools (auto-discovered) for user_id: {self.user_id}")
    
    async def llm_node(
        self, 
        chat_ctx: llm.ChatContext, 
        tools: list[llm.FunctionTool], 
        model_settings: ModelSettings
    ):
        """
        Intercepts User Input -> LLM using Agno framework.
        Sanitizes the chat context so the LLM never sees the raw PII.
        Agno automatically handles tool calling based on tool definitions.
        """
        # Ensure Agno agent is initialized
        self._initialize_agno_agent()
        
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
                            # Sanitize PII before sending to Agno
                            user_message = self._sanitize_text(user_message)
                            if user_message != item.text_content:
                                logger.info(f"Sanitized User Input before Agno: {item.text_content[:50]}... -> {user_message[:50]}...")
                        break
        
        if not user_message:
            # No user message, return default behavior
            return super().llm_node(chat_ctx, tools, model_settings)
        
        # Run Agno agent with user message
        # Agno will automatically call MCP tools as needed
        try:
            response = self.agno_agent.run(user_message)
            
            # Convert Agno response to LiveKit streaming format
            # Agno returns a RunResponse object with content
            response_text = response.content if hasattr(response, 'content') else str(response)
            
            # Stream the response back as async generator
            async def agno_response_stream():
                # Yield response in chunks to simulate streaming
                chunk_size = 50
                for i in range(0, len(response_text), chunk_size):
                    chunk = response_text[i:i + chunk_size]
                    # Sanitize output before streaming
                    sanitized_chunk = self._sanitize_text(chunk)
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
        Sanitizes the stream before the agent speaks it.
        """
        
        # We define a generator to wrap the incoming text stream
        async def safe_text_stream():
            async for chunk in text:
                # Note: Running Presidio on small chunks (tokens) is inaccurate.
                # Ideally, you should buffer by sentence. 
                # For this sample, we assume 'chunk' is substantial or we accept partial redaction risks.
                # LiveKit's LLM stream usually yields chunks; a buffer might be needed for production accuracy.
                sanitized_chunk = self._sanitize_text(chunk)
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

    # Get the first remote participant (the user)
    # In LiveKit, participants include both local and remote participants
    for participant in room.remote_participants.values():
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
                    break
                else:
                    # In console mode, metadata might be a MagicMock - skip it
                    logger.debug(f"Skipping non-string metadata: {type(participant.metadata)}")
                    continue
            except (json.JSONDecodeError, AttributeError, TypeError) as e:
                logger.debug(f"Error parsing participant metadata: {e}")
                continue

    # If no metadata found, try to extract from participant identity
    # Fallback: use participant identity if it follows the pattern voice_assistant_user_{user_id}
    if not user_id:
        for participant in room.remote_participants.values():
            identity = participant.identity
            # Check if identity is a string (not a MagicMock)
            if isinstance(identity, str) and identity.startswith("voice_assistant_user_"):
                user_id = identity.replace("voice_assistant_user_", "")
                # Use default values if metadata not available
                email = f"user_{user_id}@example.com"
                break

    # Final fallback: use environment variable or default for console mode
    if not user_id:
        user_id = os.getenv("DEFAULT_USER_ID", "12345")
        email = f"user_{user_id}@example.com"
        logger.info(f"Using default user_id from environment: {user_id}")

    # Get MCP server URL from environment or use default
    mcp_server_url = os.getenv("MCP_SERVER_URL", "http://localhost:8001/mcp")
    
    # Create JWT-authenticated MCP server with the extracted user_id
    mcp_server = JWTAuthenticatedMCPServer(
        url=mcp_server_url,
        user_id=user_id,
    )

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
        assistant.session_id = room_name
        logger.info(f"Set agent context: user_id={user_id}, session_id={room_name}")

    # Create agent session
    # Note: Using VAD (Voice Activity Detection) for turn detection instead of MultilingualModel
    # VAD handles voice activity without requiring model downloads
    agent_session = AgentSession(
        stt="assemblyai/universal-streaming:en",
        llm="openai/gpt-4.1-mini",
        tts="cartesia/sonic-3:a167e0f3-df7e-4d52-a9c3-f949145efdab",  # Male voice
        vad=silero.VAD.load(),
        # turn_detection removed - VAD handles voice activity detection without model downloads
    )

    # Start the session
    await agent_session.start(
        room=room,
        agent=assistant
    )

    # Generate initial greeting
    await agent_session.generate_reply(
        instructions="Greet the user professionally as a banking assistant and ask for their customer ID to help with their banking needs."
    )

if __name__ == "__main__":
    # Run the agent
    agents.cli.run_app(agents.WorkerOptions(entrypoint_fnc=entrypoint))
