"""
LiveKit Voice Agent - Quick Start
==================================
The simplest possible LiveKit voice agent to get you started.
Requires only OpenAI and Deepgram API keys.
"""

from typing import Any, AsyncIterable
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
from livekit.agents import Agent, AgentSession, RunContext, ModelSettings
from livekit.agents.llm import function_tool, mcp

from livekit.agents import log as agents_log

logger = agents_log.logger
from livekit.plugins import silero
from livekit.plugins.turn_detector.multilingual import MultilingualModel

from session_manager import get_session_manager

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

    # Create agent session
    agent_session = AgentSession(
        stt="assemblyai/universal-streaming:en",
        llm="openai/gpt-4.1-mini",
        tts="cartesia/sonic-3:a167e0f3-df7e-4d52-a9c3-f949145efdab",  # Male voice
        vad=silero.VAD.load(),
        turn_detection=MultilingualModel(),
        mcp_servers=[mcp_server],  # Let AgentSession handle MCP integration!
    )

    # Start the session
    await agent_session.start(
        room=room,
        agent=Assistant()
    )

    # Generate initial greeting
    await agent_session.generate_reply(
        instructions="Greet the user professionally as a banking assistant and ask for their customer ID to help with their banking needs."
    )

if __name__ == "__main__":
    # Run the agent
    agents.cli.run_app(agents.WorkerOptions(entrypoint_fnc=entrypoint))
