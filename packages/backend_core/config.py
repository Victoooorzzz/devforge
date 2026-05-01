# packages/backend-core/config.py

from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # Application
    app_name: str = "DevForge Product"
    debug: bool = False
    frontend_url: str = "http://localhost:3000"
    allowed_origins: str = "http://localhost:3000,http://localhost:3001"
    api_host: str = "0.0.0.0"
    api_port: int = 8000

    # Database
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/devforge"

    # JWT
    jwt_secret: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expiration_minutes: int = 43200  # 30 days

    # LemonSqueezy
    lemonsqueezy_api_key: str = ""
    lemonsqueezy_store_id: str = ""
    lemonsqueezy_webhook_secret: str = ""

    # Stripe (Optional)
    stripe_secret_key: str = ""
    stripe_webhook_secret: str = ""


    # Email (SMTP)
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from: str = ""

    # Cloudflare R2 (S3-compatible, used by File Cleaner)
    s3_endpoint_url: str = ""
    s3_access_key_id: str = ""
    s3_secret_access_key: str = ""
    s3_bucket_name: str = ""

    # Gemini (used by Feedback Analyzer)
    gemini_api_key: str = ""

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": False,
        "extra": "ignore",
    }


@lru_cache()
def get_settings() -> Settings:
    return Settings()
