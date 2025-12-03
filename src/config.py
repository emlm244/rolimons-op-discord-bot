"""Configuration management for RISniper."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

from dotenv import load_dotenv

load_dotenv()


class PurchaseMode(Enum):
    """Purchase mode options."""

    ALERT_CONFIRM = "alert_confirm"  # DEFAULT - Alert user, wait for button
    FULL_AUTO = "full_auto"  # Auto-buy when score >= threshold
    HYBRID = "hybrid"  # Auto 85+, confirm 70-84


class StrategyFlag(Enum):
    """Strategy flag options that modify algorithm weights."""

    QUICK_FLIPS = "quick_flips"
    VALUE_PLAYS = "value_plays"
    RARE_HUNTING = "rare_hunting"


class UGCMode(Enum):
    """UGC handling mode."""

    INCLUDE = "include"  # Allow UGC, apply score penalty
    EXCLUDE = "exclude"  # Only classic Roblox limiteds


# Strategy descriptions for info buttons
STRATEGY_INFO = {
    StrategyFlag.QUICK_FLIPS: {
        "emoji": "🔄",
        "name": "Quick Flips",
        "description": "High-liquidity items for fast resale. Smaller margins but consistent profits. Best for active traders.",
        "effect": "+15 liquidity weight, requires 20+ sales/30d",
    },
    StrategyFlag.VALUE_PLAYS: {
        "emoji": "💎",
        "name": "Value Plays",
        "description": "Deep discounts on stable items. Hold longer for bigger profit. Best for patient traders.",
        "effect": "+20 discount weight, requires 40%+ off, stable trend bonus",
    },
    StrategyFlag.RARE_HUNTING: {
        "emoji": "🏆",
        "name": "Rare Hunting",
        "description": "Target rare items with high demand. Higher risk but potential for massive returns.",
        "effect": "+25 for rare items, requires demand >= 3, <= 100 copies",
    },
}


@dataclass
class Config:
    """Application configuration."""

    # Discord
    discord_token: str = field(default_factory=lambda: os.getenv("DISCORD_TOKEN", ""))
    discord_guild_id: Optional[int] = field(
        default_factory=lambda: int(os.getenv("DISCORD_GUILD_ID", "0")) or None
    )

    # Roblox Auth
    roblosecurity: str = field(
        default_factory=lambda: os.getenv("ROBLOSECURITY", "")
    )

    # Sniper Settings
    snipe_threshold: int = field(
        default_factory=lambda: int(os.getenv("SNIPE_THRESHOLD", "70"))
    )
    alert_threshold: int = field(
        default_factory=lambda: int(os.getenv("ALERT_THRESHOLD", "50"))
    )
    max_price_per_item: int = field(
        default_factory=lambda: int(os.getenv("MAX_PRICE_PER_ITEM", "50000"))
    )
    total_budget: int = field(
        default_factory=lambda: int(os.getenv("TOTAL_BUDGET", "500000"))
    )
    poll_interval_seconds: int = field(
        default_factory=lambda: int(os.getenv("POLL_INTERVAL_SECONDS", "60"))
    )

    # Mode Settings
    purchase_mode: PurchaseMode = field(
        default_factory=lambda: PurchaseMode(
            os.getenv("PURCHASE_MODE", "alert_confirm")
        )
    )
    strategy_flags: list[StrategyFlag] = field(default_factory=list)
    ugc_mode: UGCMode = field(
        default_factory=lambda: UGCMode(os.getenv("UGC_MODE", "include"))
    )

    # Safety
    max_purchases_per_hour: int = field(
        default_factory=lambda: int(os.getenv("MAX_PURCHASES_PER_HOUR", "10"))
    )
    cooldown_between_purchases: int = field(
        default_factory=lambda: int(os.getenv("COOLDOWN_BETWEEN_PURCHASES", "30"))
    )

    # Data
    data_dir: str = field(default_factory=lambda: os.getenv("DATA_DIR", "data"))

    # API URLs
    rolimons_base_url: str = "https://www.rolimons.com"
    roblox_economy_url: str = "https://economy.roblox.com"
    roblox_auth_url: str = "https://auth.roblox.com"

    def __post_init__(self) -> None:
        """Parse strategy flags from environment."""
        flags_str = os.getenv("STRATEGY_FLAGS", "quick_flips")
        self.strategy_flags = []
        for flag in flags_str.split(","):
            flag = flag.strip().lower()
            if flag:
                try:
                    self.strategy_flags.append(StrategyFlag(flag))
                except ValueError:
                    pass
        if not self.strategy_flags:
            self.strategy_flags = [StrategyFlag.QUICK_FLIPS]

    def validate(self) -> list[str]:
        """Validate configuration. Returns list of errors."""
        errors = []
        if not self.discord_token:
            errors.append("DISCORD_TOKEN is required")
        if not self.roblosecurity:
            errors.append("ROBLOSECURITY is required for purchasing")
        if self.snipe_threshold < 0 or self.snipe_threshold > 100:
            errors.append("SNIPE_THRESHOLD must be between 0 and 100")
        if self.alert_threshold < 0 or self.alert_threshold > 100:
            errors.append("ALERT_THRESHOLD must be between 0 and 100")
        if self.alert_threshold > self.snipe_threshold:
            errors.append("ALERT_THRESHOLD should be <= SNIPE_THRESHOLD")
        return errors


# Global config instance
config = Config()
