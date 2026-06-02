from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import List

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

ENV_FILE = Path(__file__).resolve().parents[2] / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=ENV_FILE, env_file_encoding="utf-8", extra="ignore")

    app_name: str = "AI Engineer Portal API"
    app_env: str = "development"
    database_url: str = "sqlite:///./backend/test.db"
    redis_url: str = "redis://localhost:6379/0"
    cors_origins: str = Field(default="http://localhost:3000")
    anthropic_api_key: str = ""
    ai_model: str = "claude-sonnet-4-20250514"
    ai_daily_token_budget: int = 100_000
    elevenlabs_api_key: str = ""
    elevenlabs_voice_id_narration: str = "W8lBaQb9YIoddhxfQNLP"  # Single narrative voice
    elevenlabs_voice_id_a: str = "UFDAUkGzdLAEJlINT3Fx"         # Dialogue host A
    elevenlabs_voice_id_b: str = "bhJUNIXWQQ94l8eI2VUf"         # Dialogue host B
    webshare_proxy_username: str = ""   # Webshare rotating residential proxy username (proxy.webshare.io)
    webshare_proxy_password: str = ""   # Webshare rotating residential proxy password

    @property
    def cors_origins_list(self) -> List[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
