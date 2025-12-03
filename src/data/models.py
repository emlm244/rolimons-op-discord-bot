"""Data models for RISniper."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import IntEnum
from typing import Optional


class Demand(IntEnum):
    """Rolimons demand values."""

    NONE = -1
    TERRIBLE = 0
    LOW = 1
    NORMAL = 2
    HIGH = 3
    AMAZING = 4

    @property
    def display_name(self) -> str:
        """Human-readable name."""
        names = {
            -1: "None",
            0: "Terrible",
            1: "Low",
            2: "Normal",
            3: "High",
            4: "Amazing",
        }
        return names.get(self.value, "Unknown")

    @property
    def emoji(self) -> str:
        """Emoji representation."""
        emojis = {
            -1: "❓",
            0: "💀",
            1: "📉",
            2: "➡️",
            3: "📈",
            4: "🔥",
        }
        return emojis.get(self.value, "❓")


class Trend(IntEnum):
    """Rolimons trend values."""

    NONE = -1
    LOWERING = 0
    UNSTABLE = 1
    STABLE = 2
    RAISING = 3
    FLUCTUATING = 4

    @property
    def display_name(self) -> str:
        """Human-readable name."""
        names = {
            -1: "None",
            0: "Lowering",
            1: "Unstable",
            2: "Stable",
            3: "Raising",
            4: "Fluctuating",
        }
        return names.get(self.value, "Unknown")

    @property
    def emoji(self) -> str:
        """Emoji representation."""
        emojis = {
            -1: "❓",
            0: "⬇️",
            1: "〰️",
            2: "➡️",
            3: "⬆️",
            4: "📊",
        }
        return emojis.get(self.value, "❓")


@dataclass
class Item:
    """Represents a Roblox limited item with Rolimons data."""

    item_id: int
    name: str
    acronym: str = ""

    # Pricing
    rap: int = 0  # Recent Average Price
    value: int = 0  # Rolimons estimated value
    default_value: int = 0

    # Rolimons metrics
    demand: Demand = Demand.NONE
    trend: Trend = Trend.NONE
    projected: bool = False
    hyped: bool = False
    rare: bool = False

    # Additional data (from Roblox API)
    copies_remaining: Optional[int] = None
    recent_sales_30d: Optional[int] = None
    is_ugc: bool = False
    created_at: Optional[datetime] = None

    @property
    def thumbnail_url(self) -> str:
        """Generate Roblox asset thumbnail URL."""
        return f"https://www.roblox.com/asset-thumbnail/image?assetId={self.item_id}&width=420&height=420&format=png"

    @property
    def rolimons_url(self) -> str:
        """Link to Rolimons item page."""
        return f"https://www.rolimons.com/item/{self.item_id}"

    @property
    def roblox_url(self) -> str:
        """Link to Roblox catalog page."""
        return f"https://www.roblox.com/catalog/{self.item_id}"

    @property
    def display_demand(self) -> str:
        """Formatted demand string."""
        return f"{self.demand.emoji} {self.demand.display_name}"

    @property
    def display_trend(self) -> str:
        """Formatted trend string."""
        return f"{self.trend.emoji} {self.trend.display_name}"

    @property
    def item_type(self) -> str:
        """Returns 'UGC' or 'Classic'."""
        return "UGC" if self.is_ugc else "Classic"


@dataclass
class Listing:
    """A resale listing for an item."""

    item_id: int
    seller_id: int
    seller_name: str
    price: int
    product_id: int  # Needed for purchase API
    user_asset_id: int  # CRITICAL: Required for limited item purchases
    serial_number: Optional[int] = None

    @property
    def roblox_profile_url(self) -> str:
        """Link to seller's Roblox profile."""
        return f"https://www.roblox.com/users/{self.seller_id}/profile"


@dataclass
class Deal:
    """A deal from Rolimons deals page."""

    item_id: int
    item_name: str
    price: int
    value: int
    rap: int
    discount_percent: float
    seller_id: Optional[int] = None
    timestamp: datetime = field(default_factory=datetime.utcnow)

    @classmethod
    def from_item_and_listing(cls, item: Item, listing: Listing) -> Deal:
        """Create a Deal from an Item and Listing."""
        discount = (1 - listing.price / item.value) * 100 if item.value > 0 else 0
        return cls(
            item_id=item.item_id,
            item_name=item.name,
            price=listing.price,
            value=item.value,
            rap=item.rap,
            discount_percent=discount,
            seller_id=listing.seller_id,
        )


@dataclass
class PurchaseRecord:
    """Record of a completed or attempted purchase."""

    # Identification
    record_id: str  # UUID
    item_id: int
    item_name: str

    # Purchase details
    purchase_price: int
    purchase_time: datetime
    seller_id: int
    snipe_score: int
    strategy_used: str

    # Status
    success: bool = False
    error_message: Optional[str] = None

    # Current values (updated periodically)
    current_value: int = 0
    current_rap: int = 0

    # Sale details (when sold)
    sold_price: Optional[int] = None
    sold_time: Optional[datetime] = None

    @property
    def unrealized_pnl(self) -> int:
        """Profit/loss if sold at current value."""
        return self.current_value - self.purchase_price

    @property
    def unrealized_pnl_percent(self) -> float:
        """Unrealized P&L as percentage."""
        if self.purchase_price == 0:
            return 0.0
        return (self.unrealized_pnl / self.purchase_price) * 100

    @property
    def realized_pnl(self) -> Optional[int]:
        """Actual profit/loss after sale."""
        if self.sold_price is None:
            return None
        return self.sold_price - self.purchase_price

    @property
    def realized_pnl_percent(self) -> Optional[float]:
        """Realized P&L as percentage."""
        if self.sold_price is None or self.purchase_price == 0:
            return None
        return ((self.sold_price - self.purchase_price) / self.purchase_price) * 100

    @property
    def is_profitable(self) -> bool:
        """Whether the purchase is currently profitable."""
        return self.unrealized_pnl > 0

    @property
    def holding_duration(self) -> Optional[float]:
        """Days held (or until sold)."""
        end_time = self.sold_time or datetime.utcnow()
        delta = end_time - self.purchase_time
        return delta.total_seconds() / 86400  # Convert to days


@dataclass
class PortfolioStats:
    """Aggregated portfolio statistics."""

    total_spent: int = 0
    current_value: int = 0
    unrealized_pnl: int = 0
    realized_pnl: int = 0

    total_purchases: int = 0
    successful_purchases: int = 0
    failed_purchases: int = 0

    winning_trades: int = 0
    losing_trades: int = 0

    @property
    def unrealized_pnl_percent(self) -> float:
        """Unrealized P&L as percentage."""
        if self.total_spent == 0:
            return 0.0
        return (self.unrealized_pnl / self.total_spent) * 100

    @property
    def win_rate(self) -> float:
        """Percentage of profitable trades."""
        total = self.winning_trades + self.losing_trades
        if total == 0:
            return 0.0
        return (self.winning_trades / total) * 100

    @property
    def success_rate(self) -> float:
        """Percentage of successful purchases."""
        if self.total_purchases == 0:
            return 0.0
        return (self.successful_purchases / self.total_purchases) * 100
