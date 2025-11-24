"""Application configuration loaded from environment variables."""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import List, Optional


def _parse_int(value: Optional[str]) -> Optional[int]:
    if value is None:
        return None
    try:
        return int(value)
    except ValueError as exc:
        raise ValueError(f"Expected integer environment variable, got {value!r}") from exc


def _parse_int_list(value: Optional[str]) -> List[int]:
    if not value:
        return []
    parsed: List[int] = []
    for part in value.split(","):
        part = part.strip()
        if not part:
            continue
        parsed.append(_parse_int(part) or 0)
    return parsed


@dataclass(slots=True)
class Settings:
    """Runtime settings for the bot."""

    token: str
    guild_id: Optional[int]
    rolimons_base_url: str
    rolimons_api_key: Optional[str]
    op_proofs_url: Optional[str]
    alert_rate_limit_seconds: int = 60
    alert_poll_seconds: int = 300
    alert_lookback_days: int = 30
    staff_role_ids: List[int] = field(default_factory=list)
    dm_proofs_lookback_months: int = 6

    @classmethod
    def from_env(cls) -> "Settings":
        token = os.getenv("DISCORD_TOKEN")
        if not token:
            raise RuntimeError("DISCORD_TOKEN environment variable is required")

        guild_id = _parse_int(os.getenv("DISCORD_GUILD_ID"))
        rolimons_base_url = os.getenv("ROLIMONS_BASE_URL", "https://www.rolimons.com")
        rolimons_api_key = os.getenv("ROLIMONS_API_KEY")
        op_proofs_url = os.getenv("ROLIMONS_PROOFS_URL")

        alert_rate_limit_seconds = _parse_int(os.getenv("ALERT_RATE_LIMIT_SECONDS")) or 60
        alert_poll_seconds = _parse_int(os.getenv("ALERT_POLL_SECONDS")) or 300
        alert_lookback_days = _parse_int(os.getenv("ALERT_LOOKBACK_DAYS")) or 30
        dm_proofs_lookback_months = _parse_int(os.getenv("DM_PROOFS_LOOKBACK_MONTHS")) or 6
        staff_role_ids = _parse_int_list(os.getenv("STAFF_ROLE_IDS"))

        return cls(
            token=token,
            guild_id=guild_id,
            rolimons_base_url=rolimons_base_url,
            rolimons_api_key=rolimons_api_key,
            op_proofs_url=op_proofs_url,
            alert_rate_limit_seconds=alert_rate_limit_seconds,
            alert_poll_seconds=alert_poll_seconds,
            alert_lookback_days=alert_lookback_days,
            dm_proofs_lookback_months=dm_proofs_lookback_months,
            staff_role_ids=staff_role_ids,
        )


settings = Settings.from_env()
