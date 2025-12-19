from pydantic_settings import BaseSettings
from pydantic import field_validator, Field
from typing import List, Union

class Settings(BaseSettings):
    # App
    APP_NAME: str = "Annotation Platform API"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    ENVIRONMENT: str = "production"

    # Database
    DATABASE_URL: str = Field(..., description="PostgreSQL database URL")

    # Supabase
    SUPABASE_URL: str = Field(..., description="Supabase project URL")
    SUPABASE_KEY: str = Field(..., description="Supabase anon/public key")
    SUPABASE_SERVICE_KEY: str = Field(..., description="Supabase service role key")

    # JWT/Auth
    JWT_SECRET: str = Field(..., description="Secret key for JWT token signing")
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # Alias for compatibility - now properly handled
    SECRET_KEY: str = Field(default="", description="Alias for JWT_SECRET")

    # CORS - handles both string and list formats
    CORS_ORIGINS: Union[List[str], str] = Field(
        default=["http://localhost:3000"],
        description="Comma-separated list of allowed CORS origins"
    )

    # Label Studio
    LABEL_STUDIO_URL: str = "http://localhost:8080"
    LABEL_STUDIO_API_KEY: str = Field(..., description="Label Studio API key")

    # Storage
    STORAGE_BUCKET: str = "annotation-assets"
    MAX_FILE_SIZE: int = 10485760  # 10MB in bytes

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True
        extra = "ignore"  # Ignore extra fields in .env
    
    # Validator to handle CORS_ORIGINS as comma-separated string or list
    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors_origins(cls, v):
        if isinstance(v, str):
            # Remove brackets and quotes if present (handles your current format)
            v = v.strip()
            if v.startswith('[') and v.endswith(']'):
                v = v[1:-1]  # Remove brackets
            # Split by comma and strip whitespace/quotes
            origins = [origin.strip().strip('"').strip("'") for origin in v.split(",")]
            return origins
        return v
    
    # Ensure SECRET_KEY mirrors JWT_SECRET if not explicitly set
    @field_validator("SECRET_KEY", mode="before")
    @classmethod
    def set_secret_key(cls, v, info):
        # If SECRET_KEY is not set but JWT_SECRET is, use JWT_SECRET
        if not v and info.data.get("JWT_SECRET"):
            return info.data["JWT_SECRET"]
        return v

# Create settings instance
settings = Settings()