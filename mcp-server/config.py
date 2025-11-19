"""
Configuration settings for MCP Server.
"""

import os
from typing import List
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings."""
    
    # Server settings
    HOST: str = os.getenv("MCP_HOST", "0.0.0.0")
    PORT: int = int(os.getenv("MCP_PORT", "8001"))
    DEBUG: bool = os.getenv("MCP_DEBUG", "false").lower() == "true"
    
    # CORS settings
    CORS_ORIGINS: List[str] = os.getenv(
        "CORS_ORIGINS",
        "http://localhost:3000,http://localhost:8080"
    ).split(",")
    
    # JWT settings
    JWT_SECRET_KEY: str = os.getenv("MCP_JWT_SECRET_KEY", "your-secret-key-change-in-production")
    JWT_ALGORITHM: str = os.getenv("MCP_JWT_ALGORITHM", "HS256")
    JWT_ISSUER: str = os.getenv("MCP_JWT_ISSUER", "orchestrator")
    
    # Banking API settings (mock for now)
    BANKING_API_URL: str = os.getenv("BANKING_API_URL", "http://localhost:8002")
    BANKING_API_TIMEOUT: int = int(os.getenv("BANKING_API_TIMEOUT", "5"))
    
    # Cache settings
    CACHE_ENABLED: bool = os.getenv("CACHE_ENABLED", "true").lower() == "true"
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    
    # Logging
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")

    # Stripe settings
    STRIPE_SECRET_KEY: str = os.getenv("STRIPE_SECRET_KEY", "sk_test_51SV4tR6iHKfkinmUligxtDw9VcVbScK20lx71vF3MyjV9UIisbo9cdaV6Ed0xuuDA464Q445jJ8F1NvSTWP46aGn00Ab2kufqG")
    STRIPE_PUBLISHABLE_KEY: str = os.getenv("STRIPE_PUBLISHABLE_KEY", "pk_test_...")
    
    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()

