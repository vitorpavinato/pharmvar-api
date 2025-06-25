"""
Application configuration settings using Pydantic Settings.
Supports environment variables and .env files.
"""

import os
from typing import Optional, List
from pydantic_settings import BaseSettings
from pydantic import validator


class Settings(BaseSettings):
    """Application settings with environment variable support."""
    
    # Application
    app_name: str = "PharmVar API Explorer"
    app_version: str = "0.1.0"
    debug: bool = False
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    
    # Database
    database_url: Optional[str] = None
    db_host: str = "localhost"
    db_port: int = 5432
    db_name: str = "pharmvar_db"
    db_user: str = "pharmvar_user"
    db_password: str = "pharmvar_pass"
    
    # Redis (Caching)
    redis_url: Optional[str] = None
    redis_host: str = "localhost" 
    redis_port: int = 6379
    redis_db: int = 0
    
    # External APIs
    ensembl_api_base_url: str = "https://rest.ensembl.org"
    clinvar_api_base_url: str = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
    pharmvar_api_base_url: str = "https://www.pharmvar.org/api"
    
    # API Keys
    ncbi_api_key: Optional[str] = None
    
    # Rate Limiting (requests per second)
    ensembl_rate_limit: float = 14.0  # Ensembl allows 15/sec
    clinvar_rate_limit: float = 2.0   # Conservative without API key
    api_rate_limit: int = 100         # Our API rate limit per minute
    
    # Security
    secret_key: str = "change-this-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    
    # CORS
    allowed_origins: List[str] = ["http://localhost:3000", "http://localhost:8080"]
    
    # Logging
    log_level: str = "INFO"
    log_format: str = "standard"  # "standard" or "json"
    
    # Celery (Background tasks)
    celery_broker_url: Optional[str] = None
    celery_result_backend: Optional[str] = None
    
    @validator("database_url", pre=True)
    def assemble_db_connection(cls, v: Optional[str], values: dict) -> str:
        """Build database URL from components if not provided."""
        if isinstance(v, str):
            return v
        return (
            f"postgresql://{values.get('db_user')}:{values.get('db_password')}"
            f"@{values.get('db_host')}:{values.get('db_port')}/{values.get('db_name')}"
        )
    
    @validator("redis_url", pre=True)
    def assemble_redis_connection(cls, v: Optional[str], values: dict) -> str:
        """Build Redis URL from components if not provided."""
        if isinstance(v, str):
            return v
        return (
            f"redis://{values.get('redis_host')}:{values.get('redis_port')}"
            f"/{values.get('redis_db')}"
        )
    
    @validator("celery_broker_url", pre=True)
    def assemble_celery_broker(cls, v: Optional[str], values: dict) -> str:
        """Use Redis URL as Celery broker if not specified."""
        if isinstance(v, str):
            return v
        return values.get("redis_url") or f"redis://localhost:6379/0"
    
    @validator("celery_result_backend", pre=True)
    def assemble_celery_backend(cls, v: Optional[str], values: dict) -> str:
        """Use Redis URL as Celery result backend if not specified."""
        if isinstance(v, str):
            return v
        return values.get("redis_url") or f"redis://localhost:6379/0"
    
    @validator("clinvar_rate_limit", pre=True)
    def adjust_clinvar_rate_limit(cls, v: float, values: dict) -> float:
        """Adjust ClinVar rate limit based on API key availability."""
        if values.get("ncbi_api_key"):
            return 9.0  # With API key: 10/sec (use 9 to be safe)
        return 2.0      # Without API key: 3/sec (use 2 to be safe)
    
    @validator("allowed_origins", pre=True)
    def parse_cors_origins(cls, v) -> List[str]:
        """Parse CORS origins from string or list."""
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",")]
        return v
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


# Global settings instance
settings = Settings()


def get_settings() -> Settings:
    """Get application settings (for dependency injection)."""
    return settings