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

    # CORS
    CORS_ORIGINS: Union[List[str], str] = Field(
        default=["http://localhost:3000"],
        description="Comma-separated list of allowed CORS origins"
    )

    # Label Studio
    LABEL_STUDIO_URL: str = "http://localhost:8080"
    LABEL_STUDIO_API_KEY: str = Field(..., description="Label Studio API key")

    # Storage
    STORAGE_BUCKET: str = "annotation-assets"
    MAX_FILE_SIZE: int = 10485760

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": True,
        "extra": "ignore",
    }

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors_origins(cls, v):
        if isinstance(v, str):
            v = v.strip()
            if v.startswith("[") and v.endswith("]"):
                v = v[1:-1]
            return [origin.strip().strip('"').strip("'") for origin in v.split(",")]
        return v

settings = Settings()