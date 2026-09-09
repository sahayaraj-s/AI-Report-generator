"""
Central settings, loaded from environment variables (.env in local dev).
"""
from __future__ import annotations
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    dev_mode: bool = True

    database_url: str = "sqlite:///./placement.db"

    firebase_service_account_json: str = ""

    gemini_api_key: str = ""
    gemini_model: str = "gemini-1.5-flash"

    frontend_origin: str = "http://localhost:5173"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
