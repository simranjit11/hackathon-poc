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
# Note: VoicePipelineAgent and AgentTranscriptionOptions are not available in current livekit-agents version
# Transcription options may need to be configured differently

# Presidio Imports
from presidio_analyzer import AnalyzerEngine, PatternRecognizer, Pattern
from presidio_anonymizer import AnonymizerEngine
from presidio_anonymizer.entities import OperatorConfig
import re

# Initialize Presidio Engines lazily (only when needed)
# This avoids proxy/network issues during import
_analyzer = None
_anonymizer = None

def get_analyzer():
    """Get or create Presidio analyzer engine with custom OTP recognizer."""
    global _analyzer
    if _analyzer is None:
        try:
            #Create base analyzer
            _analyzer = AnalyzerEngine()
            
            # Add custom OTP recognizer
            # Pattern 1: Numeric OTPs (4-8 digits, optionally with spaces/dashes)
            numeric_otp_pattern = r'\b\d{4,8}\b|\b\d{3,4}[-\s]\d{3,4}\b'
            
            # Pattern 2: Word-based OTPs (e.g., "one two three four five")
            # Match sequences of number words (3-8 words) - basic number words only
            otp_words = r'(?:one|two|three|four|five|six|seven|eight|nine|zero)'
            # Match 3-8 consecutive number words - this is the core OTP value pattern
            otp_value_only = rf'\b(?:{otp_words}\s+){{2,7}}{otp_words}\b'
            
            # Pattern 3: OTP with context - matches the full phrase but we'll extract just the value
            # This helps with context scoring but the actual match should be the value part
            otp_with_context_full = rf'\b(?:my|the|your)?(?:otp|code|pin|password|passcode|verification\s+code)\s+is\s+((?:{otp_words}\s+){{2,7}}{otp_words})\b'
            
            # Create recognizers for different patterns
            numeric_otp_recognizer = PatternRecognizer(
                supported_entity="OTP",
                patterns=[
                    Pattern(
                        name="numeric_otp",
                        regex=numeric_otp_pattern,
                        score=0.8
                    )
                ],
                context=["otp", "code", "pin", "password", "passcode", "verification code", "one-time password", "verification"]
            )
            
            # Primary recognizer for word-based OTP values
            # This matches just the number words sequence (e.g., "one two three four five")
            word_otp_recognizer = PatternRecognizer(
                supported_entity="OTP",
                patterns=[
                    Pattern(
                        name="otp_value_only",
                        regex=otp_value_only,
                        score=0.8
                    )
                ],
                context=["otp", "code", "pin", "password", "passcode", "verification code", "one-time password", "my", "the", "your", "is"],
                # Increase context score when OTP-related words are nearby
                supported_language="en"
            )
            
            # Add both recognizers
            _analyzer.registry.add_recognizer(numeric_otp_recognizer)
            _analyzer.registry.add_recognizer(word_otp_recognizer)
            
        except Exception as e:
            # If spaCy model is not found, provide helpful error
            import sys
            print(f"Error initializing Presidio Analyzer: {e}", file=sys.stderr)
            print("Please run: uv run python -m spacy download en_core_web_lg", file=sys.stderr)
            raise
    return _analyzer

def get_anonymizer():
    """Get or create Presidio anonymizer engine."""
    global _anonymizer
    if _anonymizer is None:
        _anonymizer = AnonymizerEngine()
    return _anonymizer

from datetime import datetime, timedelta, timezone
import os

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
    
    def llm_node(
        self, 
        chat_ctx: llm.ChatContext, 
        tools: list[llm.FunctionTool], 
        model_settings: ModelSettings
    ):
        """
        Intercepts User Input -> LLM.
        Sanitizes the chat context so the LLM never sees the raw PII.
        """
        # Iterate through the context and sanitize the latest user message
        # Note: ChatContext uses items property, not messages attribute
        items = chat_ctx.items
        if items:
            # Find the last ChatMessage item
            for item in reversed(items):
                # Check if it's a ChatMessage (has 'type' attribute that equals 'message')
                if hasattr(item, 'type') and item.type == 'message' and hasattr(item, 'role'):
                    if item.role == "user":
                        # Use text_content property to get all text content
                        original_text = item.text_content
                        if original_text:
                            sanitized_text = self._sanitize_text(original_text)
                            
                            # Update the message content (replace first text content item)
                            if isinstance(item.content, list) and len(item.content) > 0:
                                # Replace the first text content with sanitized version
                                for i, content in enumerate(item.content):
                                    if isinstance(content, str):
                                        item.content[i] = sanitized_text
                                        break
                            
                            if original_text != sanitized_text:
                                logger.info(f"Sanitized User Input: {original_text} -> {sanitized_text}")
                    break

        # Pass the sanitized context to the default LLM behavior
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
    # Get MCP server URL from environment or use default
    mcp_server_url = os.getenv("MCP_SERVER_URL", "http://localhost:8001/mcp")
    
    # For now, use a default user_id - in production, extract from room/participant
    # TODO: Extract user_id from room participant metadata or JWT token
    default_user_id = os.getenv("DEFAULT_USER_ID", "12345")
    
    # Create JWT-authenticated MCP server
    mcp_server = JWTAuthenticatedMCPServer(
        url=mcp_server_url,
        user_id=default_user_id,
    )
    
    session = AgentSession(
        stt="assemblyai/universal-streaming:en",
        llm="openai/gpt-4.1-mini",
        tts="cartesia/sonic-3:a167e0f3-df7e-4d52-a9c3-f949145efdab",  # Male voice
        vad=silero.VAD.load(),
        turn_detection=MultilingualModel(),
        mcp_servers=[mcp_server],  # Let AgentSession handle MCP integration!
    )

    # Start the session
    await session.start(
        room=ctx.room,
        agent=Assistant()
    )

    # Generate initial greeting
    await session.generate_reply(
        instructions="Greet the user professionally as a banking assistant and ask for their customer ID to help with their banking needs."
    )

if __name__ == "__main__":
    # Run the agent
    agents.cli.run_app(agents.WorkerOptions(entrypoint_fnc=entrypoint))
