import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    # Database
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "postgresql+psycopg://postgres:123456@localhost:5432/social_security"
    )
    
    # Security
    JWT_SECRET_KEY: str = os.getenv("JWT_SECRET_KEY", "your-secret-key-change-in-production")
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440  # 24 hours
    
    # CORS
    CORS_ORIGINS: list = os.getenv(
        "CORS_ORIGINS",
        "http://localhost:5173,http://localhost:3000"
    ).split(",")
    
    # API
    API_V1_STR: str = "/api"
    PROJECT_NAME: str = "Community Safety Alert API"
    
    # Spider
    SPIDER_ENABLED: bool = True
    SPIDER_INTERVAL: int = 21600  # 6 hours
    SOCRATA_APP_TOKEN: str = os.getenv("SOCRATA_APP_TOKEN", "").strip()

    # Email (password reset)
    SMTP_HOST: str = os.getenv("SMTP_HOST", "")
    SMTP_PORT: int = int(os.getenv("SMTP_PORT", "587"))
    SMTP_USERNAME: str = os.getenv("SMTP_USERNAME", "")
    SMTP_PASSWORD: str = os.getenv("SMTP_PASSWORD", "")
    SMTP_USE_TLS: bool = os.getenv("SMTP_USE_TLS", "true").lower() == "true"
    SMTP_FROM_EMAIL: str = os.getenv("SMTP_FROM_EMAIL", "noreply@community-safety.local")
    SMTP_FROM_NAME: str = os.getenv("SMTP_FROM_NAME", "Community Safety Alert")
    EMAIL_DEV_MODE: bool = os.getenv("EMAIL_DEV_MODE", "true").lower() == "true"

    # LLM assistant (OpenAI-compatible chat completion API)
    LLM_API_BASE_URL: str = os.getenv("LLM_API_BASE_URL", "https://api.openai.com/v1")
    LLM_API_KEY: str = os.getenv("LLM_API_KEY", "")
    LLM_MODEL: str = os.getenv("LLM_MODEL", "gpt-4o-mini")
    LLM_TIMEOUT_SECONDS: int = int(os.getenv("LLM_TIMEOUT_SECONDS", "30"))
    LLM_MAX_TOKENS: int = int(os.getenv("LLM_MAX_TOKENS", "500"))
    LLM_TEMPERATURE: float = float(os.getenv("LLM_TEMPERATURE", "0.3"))
    
    class Config:
        case_sensitive = True

settings = Settings()
