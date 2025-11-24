from __future__ import annotations

from pathlib import Path

from pydantic import AnyHttpUrl, BaseSettings, Field, validator


class Settings(BaseSettings):
    """Application configuration loaded from environment variables."""

    discord_token: str = Field(default="", env="DISCORD_TOKEN")
    guild_ids: list[int] = Field(default_factory=list, env="GUILD_IDS")
    rolimons_items_url: AnyHttpUrl = Field(
        default="https://www.rolimons.com/itemapi/itemdetails", env="ROLIMONS_ITEMS_URL"
    )
    rolimons_proofs_url: AnyHttpUrl = Field(
        default="https://www.rolimons.com/proofs", env="ROLIMONS_PROOFS_URL"
    )
    data_dir: Path = Field(default=Path("data"), env="DATA_DIR")
    alert_poll_seconds: int = Field(default=1800, env="ALERT_POLL_SECONDS")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

    @validator("guild_ids", pre=True)
    def split_guild_ids(cls, value: str | list[int] | None):  # type: ignore[override]
        if value is None or value == "":
            return []
        if isinstance(value, list):
            return value
        return [int(g.strip()) for g in str(value).split(",") if g.strip()]


settings = Settings()
