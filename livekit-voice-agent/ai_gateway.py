"""
AI Gateway module for secure model routing and authentication.
"""

import os
import uuid
from agno.models.openai import OpenAILike


class AIGateway(OpenAILike):
    """
    AI Gateway connector for secure model access.
    
    Reads configuration from environment variables:
    - AI_GATEWAY_ENDPOINT
    - AI_GATEWAY_API_KEY
    """
    
    def __init__(self, model_id: str, agent_id: str = None):
        """
        Initialize AI Gateway connection.
        
        Args:
            model_id: Model deployment ID (e.g., "gpt-4.1", "gpt-4.1-mini")
            agent_id: Agent identifier (UUID v4). If not provided, uses hardcoded constant UUID.
            
        Raises:
            ValueError: If configuration is missing or invalid
        """
        if not model_id:
            raise ValueError("model_id is required")
        
        # Use hardcoded constant UUID for agent_id
        # This ensures consistent agent identification across all requests
        if agent_id:
            try:
                # Validate if provided UUID is valid
                uuid.UUID(agent_id, version=4)
                valid_agent_id = agent_id
            except (ValueError, AttributeError):
                # Invalid UUID provided, use hardcoded constant
                valid_agent_id = "550e8400-e29b-41d4-a716-446655440000"  # Hardcoded constant UUID
        else:
            # Use hardcoded constant UUID
            valid_agent_id = "550e8400-e29b-41d4-a716-446655440000"  # Hardcoded constant UUID
        
        # Read config from environment
        endpoint = os.getenv("AI_GATEWAY_ENDPOINT")
        api_key = os.getenv("AI_GATEWAY_API_KEY")
        
        if not endpoint or not api_key:
            raise ValueError(
                "AI Gateway not configured. Set AI_GATEWAY_ENDPOINT and AI_GATEWAY_API_KEY"
            )
        
        # Initialize OpenAI-compatible model
        super().__init__(
            id=model_id,
            base_url=f"{endpoint}/deployments/{model_id}",
            extra_query={"api-version": "2024-10-21"},
            extra_headers={
                "x-agent-id": valid_agent_id,
                "api-key": api_key
            },
        )

