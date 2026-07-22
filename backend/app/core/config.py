from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import List

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

ENV_FILE = Path(__file__).resolve().parents[2] / ".env"

# Anthropic model ids that have been retired (return 404). Remap transparently so
# a stale value baked into the VPS .env can't break the whole AI layer.
_RETIRED_MODELS = {"claude-sonnet-4-20250514": "claude-sonnet-4-6"}


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=ENV_FILE, env_file_encoding="utf-8", extra="ignore")

    app_name: str = "AI Engineer Portal API"
    app_env: str = "development"
    database_url: str = "sqlite:///./backend/test.db"
    redis_url: str = "redis://localhost:6379/0"
    cors_origins: str = Field(default="http://localhost:3000")
    anthropic_api_key: str = ""
    ai_model: str = "claude-sonnet-4-6"  # claude-sonnet-4-20250514 was retired (404)
    # Paper editing (Critique) is a high-value, low-frequency task → use the strongest
    # model just here, independent of the shared ai_model (keeps high-frequency tools
    # like dub translation / podcast on cheaper Sonnet).
    critique_model: str = "claude-opus-4-8"
    # Korean course: cheap conversational model for the roleplay boss + a Korean TTS voice.
    korean_model: str = "claude-sonnet-4-6"
    minimax_korean_voice_id: str = "Korean_SweetGirl"  # override via env MINIMAX_KOREAN_VOICE_ID
    # 紫微/灵签 解盘也是高价值、低频任务 → 用最强模型（与高频的 ai_model 解耦）。
    oracle_model: str = "claude-opus-4-8"
    # 一次性「认领旧命理数据」口令（无归属的 device_id=NULL 行划归当前浏览器）。
    # 留空 = 认领禁用；在 VPS .env 设 ZIWEI_CLAIM_CODE 才能认领。
    ziwei_claim_code: str = ""
    # 自动收养旧紫微档案：第一台带 device_id 访问的浏览器把 NULL 档案收归自己。
    # 默认开（部署后站主一刷新即找回旧档案，无需口令/改 .env）；认领完可设 ZIWEI_AUTO_ADOPT=0 关。
    ziwei_auto_adopt: bool = True
    # 付费点数（灰度）：默认关——一切就绪后设 ZIWEI_REQUIRE_CREDITS=true 开闸收费。
    ziwei_require_credits: bool = False
    ziwei_free_credits: int = 3  # 新账号赠送点数
    # Stripe 跨境收款（支付宝/微信）。空 = 未配置，购买端点返回 503。
    stripe_secret_key: str = ""
    stripe_webhook_secret: str = ""
    # SMTP 邮箱找回验证码。空 = 未配置，找回端点 503（device 找回码仍可用）。
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from: str = ""
    ai_daily_token_budget: int = 100_000

    @field_validator("ai_model")
    @classmethod
    def _resolve_retired_model(cls, v: str) -> str:
        return _RETIRED_MODELS.get((v or "").strip(), v)
    openai_api_key: str = ""  # OpenAI Whisper (录 Scribe transcription)
    # MiniMax (海螺) TTS — purpose-built for Mandarin, replaces ElevenLabs
    minimax_api_key: str = ""
    minimax_group_id: str = ""
    minimax_api_base: str = "https://api.minimax.io"
    minimax_model: str = "speech-2.6-hd"
    minimax_oracle_voice_id: str = "Chinese (Mandarin)_Radio_Host"  # 解盘师默认嗓音，可经 env MINIMAX_ORACLE_VOICE_ID 覆盖
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
