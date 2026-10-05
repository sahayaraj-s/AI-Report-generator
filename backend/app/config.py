"""
Central settings, loaded from environment variables (.env in local dev).
"""
from __future__ import annotations
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    dev_mode: bool = False

    database_url: str = "sqlite:///./placement.db"

    firebase_service_account_json: str = ""

    gemini_api_key: str = ""
    # Model configuration with auto-fallback chain
    gemini_model: str = "gemini-3.6-flash"
    gemini_model_default: str = "gemini-3.6-flash"
    gemini_model_fast: str = "gemini-3.5-flash-lite"
    gemini_model_deep: str = "gemini-3.8-flash"
    gemini_fallbacks: str = "gemini-3.6-flash,gemini-3.5-flash,gemini-3.5-flash-lite,gemini-3.1-flash-lite"
    gemini_timeout_seconds: float = 20.0
    enable_image_gen: bool = False
    rate_limit_per_minute: int = 60

    cors_origins: str = "http://localhost:5173"
    frontend_origin: str = "http://localhost:5173"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
