from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # App
    app_env: str = "development"
    app_secret_key: str = "change-me"
    app_debug: bool = True

    # Database
    database_url: str = "postgresql+asyncpg://cm_user:cm_password@localhost:5432/content_machine"

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # S3 / MinIO
    s3_endpoint: str = "http://localhost:9000"
    s3_access_key: str = "minioadmin"
    s3_secret_key: str = "minioadmin"
    s3_bucket: str = "content-machine"
    s3_region: str = "us-east-1"

    # LLM
    openai_api_key: str = ""
    anthropic_api_key: str = ""
    llm_provider: str = "openai"  # openai | anthropic
    llm_model: str = "gpt-4o"

    # TTS
    elevenlabs_api_key: str = ""
    elevenlabs_voice_id: str = ""
    tts_provider: str = "elevenlabs"  # elevenlabs | openai

    # Social
    tiktok_access_token: str = ""
    instagram_access_token: str = ""
    instagram_business_account_id: str = ""

    # Monitoring
    sentry_dsn: str = ""
    log_level: str = "INFO"

    class Config:
        env_file = ".env"


@lru_cache
def get_settings() -> Settings:
    return Settings()
