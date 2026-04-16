from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "Bangumi Anime Reception Analyst"
    app_env: str = "dev"
    api_prefix: str = "/api/v1"
    output_root: Path = Path("outputs")

    bangumi_base_url: str = "https://api.bgm.tv"
    bangumi_token: str = Field(default="")
    bangumi_user_agent: str = Field(
        default="BangumiAnimeReceptionAnalyst/0.1 (contact-required)"
    )
    bangumi_timeout_seconds: float = 30.0
    bangumi_request_pause_seconds: float = 0.2

    agent_model: str = "vertex_ai/gemini-2.5-flash"
    vertex_project: str | None = None
    vertex_location: str = "us-central1"


@lru_cache
def get_settings() -> Settings:
    return Settings()
