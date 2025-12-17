from pydantic_settings import BaseSettings
from typing import List

class Settings(BaseSettings):
    # App
    APP_NAME: str = "Annotation Platform API"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    ENVIRONMENT: str = "production"

    # Database
    DATABASE_URL: str

    # Supabase
    SUPABASE_URL: str
    SUPABASE_KEY: str
    SUPABASE_SERVICE_KEY: str

    # JWT (You already have this! Just add SECRET_KEY as an alias)
    JWT_SECRET: str
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # Add this property to use JWT_SECRET as SECRET_KEY (for compatibility)
    @property
    def SECRET_KEY(self) -> str:
        return self.JWT_SECRET

    # CORS
    CORS_ORIGINS: List[str] = ["http://localhost:3000"]

    # Label Studio
    LABEL_STUDIO_URL: str = "http://localhost:8080"
    LABEL_STUDIO_API_KEY: str

    # Storage
    STORAGE_BUCKET: str = "annotation-assets"
    MAX_FILE_SIZE: int = 10485760  # 10MB

    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings()