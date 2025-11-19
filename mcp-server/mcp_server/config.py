"""
Configuration settings for MCP Server.
"""

import os
from typing import List
try:
    from pydantic_settings import BaseSettings, SettingsConfigDict
except ImportError:
    # Fallback for older pydantic versions
    from pydantic import BaseSettings
    try:
        from pydantic import ConfigDict as SettingsConfigDict
    except ImportError:
        # Very old pydantic - use class Config
        SettingsConfigDict = None


class Settings(BaseSettings):
    """Application settings."""
    
    # Server settings
    host: str = "0.0.0.0"
    port: int = 8001
    debug: bool = False
    mcp_path: str = "/mcp"
    
    # CORS settings
    cors_origins: List[str] = ["http://localhost:3000", "http://localhost:8080"]
    
    # JWT settings
    jwt_secret_key: str = "your-secret-key-change-in-production"
    jwt_algorithm: str = "HS256"
    jwt_issuer: str = "orchestrator"
    
    # Database settings
    database_url: str = "postgresql://postgres:postgres@localhost:5432/banking"
    database_pool_min_size: int = 5
    database_pool_max_size: int = 20
    
    # Cache settings
    cache_enabled: bool = True
    redis_url: str = "redis://localhost:6379/0"
    
    # Logging
    log_level: str = "INFO"
    
    if SettingsConfigDict:
        model_config = SettingsConfigDict(
            env_file=".env",
            case_sensitive=False,
            extra="ignore"
        )
    else:
        class Config:
            env_file = ".env"
            case_sensitive = False
            extra = "ignore"
    
    def __init__(self, **kwargs):
        # Map environment variables to field names
        env_map = {
            "MCP_HOST": "host",
            "MCP_PORT": "port",
            "MCP_DEBUG": "debug",
            "MCP_PATH": "mcp_path",
            "MCP_JWT_SECRET_KEY": "jwt_secret_key",
            "MCP_JWT_ALGORITHM": "jwt_algorithm",
            "MCP_JWT_ISSUER": "jwt_issuer",
            "DATABASE_URL": "database_url",
            "DATABASE_POOL_MIN_SIZE": "database_pool_min_size",
            "DATABASE_POOL_MAX_SIZE": "database_pool_max_size",
            "CACHE_ENABLED": "cache_enabled",
            "REDIS_URL": "redis_url",
            "LOG_LEVEL": "log_level",
            "CORS_ORIGINS": "cors_origins",
        }
        
        # Override with environment variables
        for env_key, field_name in env_map.items():
            env_value = os.getenv(env_key)
            if env_value is not None:
                # Remove surrounding quotes if present
                if isinstance(env_value, str) and len(env_value) >= 2 and env_value[0] == '"' and env_value[-1] == '"':
                    env_value = env_value[1:-1]
                
                if field_name in ["port", "database_pool_min_size", "database_pool_max_size"]:
                    kwargs[field_name] = int(env_value)
                elif field_name in ["debug", "cache_enabled"]:
                    kwargs[field_name] = env_value.lower() == "true"
                elif field_name == "cors_origins":
                    kwargs[field_name] = env_value.split(",")
                else:
                    kwargs[field_name] = env_value
        
        super().__init__(**kwargs)
    
    # Property aliases for backward compatibility
    @property
    def HOST(self) -> str:
        return self.host
    
    @property
    def PORT(self) -> int:
        return self.port
    
    @property
    def DEBUG(self) -> bool:
        return self.debug
    
    @property
    def MCP_PATH(self) -> str:
        return self.mcp_path
    
    @property
    def CORS_ORIGINS(self) -> List[str]:
        return self.cors_origins
    
    @property
    def JWT_SECRET_KEY(self) -> str:
        return self.jwt_secret_key
    
    @property
    def JWT_ALGORITHM(self) -> str:
        return self.jwt_algorithm
    
    @property
    def JWT_ISSUER(self) -> str:
        return self.jwt_issuer
    
    @property
    def DATABASE_URL(self) -> str:
        return self.database_url
    
    @property
    def DATABASE_POOL_MIN_SIZE(self) -> int:
        return self.database_pool_min_size
    
    @property
    def DATABASE_POOL_MAX_SIZE(self) -> int:
        return self.database_pool_max_size
    
    @property
    def CACHE_ENABLED(self) -> bool:
        return self.cache_enabled
    
    @property
    def REDIS_URL(self) -> str:
        return self.redis_url
    
    @property
    def LOG_LEVEL(self) -> str:
        return self.log_level


settings = Settings()
