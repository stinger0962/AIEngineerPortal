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
    # MiniMax (海螺) TTS — purpose-built for Mandarin, replaces ElevenLabs
    minimax_api_key: str = ""
    minimax_group_id: str = ""
    minimax_api_base: str = "https://api.minimax.io"
    minimax_model: str = "speech-2.6-hd"
    # Voice selection is driven by VOICE_CATALOG in podcast_service.py (curated pool
    # + random picker), not by fixed env vars.
    webshare_proxy_username: str = ""   # Webshare rotating residential proxy username (proxy.webshare.io)
    webshare_proxy_password: str = ""   # Webshare rotating residential proxy password

    @property
    def cors_origins_list(self) -> List[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
