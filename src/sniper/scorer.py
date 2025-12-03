"""THE ALGORITHM - Multi-factor scoring system for snipe opportunities.

This is the brain of the sniper. It calculates a score from 0-100 based on
multiple factors including discount, demand, trend, liquidity, and stability.

Strategy flags modify the base weights to favor different trading styles:
- Quick Flips: Favors high-liquidity items for fast turnaround
- Value Plays: Favors deep discounts on stable items
- Rare Hunting: Favors rare items with high demand
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

from src.config import config, StrategyFlag, UGCMode
from src.data.models import Item, Demand, Trend


class ScoreTier(Enum):
    """Score tier classifications."""

    EXCELLENT = "excellent"  # 85-100: Auto-buy immediately
    GOOD = "good"  # 70-84: Auto-buy with confirmation
    RISKY = "risky"  # 50-69: Alert only
    REJECT = "reject"  # 0-49: Ignore

    @property
    def emoji(self) -> str:
        """Emoji for the tier."""
        emojis = {
            "excellent": "🟢",
            "good": "🟡",
            "risky": "🟠",
            "reject": "🔴",
        }
        return emojis.get(self.value, "❓")

    @property
    def display_name(self) -> str:
        """Display name for the tier."""
        return self.value.upper()

    @classmethod
    def from_score(cls, score: int) -> ScoreTier:
        """Get tier from score value."""
        if score >= 85:
            return cls.EXCELLENT
        elif score >= 70:
            return cls.GOOD
        elif score >= 50:
            return cls.RISKY
        else:
            return cls.REJECT


@dataclass
class ScoreBreakdown:
    """Detailed breakdown of how a score was calculated."""

    # Base component scores
    discount_score: int = 0
    demand_score: int = 0
    trend_score: int = 0
    liquidity_score: int = 0
    stability_score: int = 0

    # Bonuses
    rare_bonus: int = 0
    classic_bonus: int = 0

    # Penalties
    hype_penalty: int = 0
    ugc_penalty: int = 0

    # Strategy modifiers
    strategy_modifier: int = 0
    strategy_name: str = ""

    # Final calculation
    base_score: int = 0
    final_score: int = 0

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "discount": self.discount_score,
            "demand": self.demand_score,
            "trend": self.trend_score,
            "liquidity": self.liquidity_score,
            "stability": self.stability_score,
            "rare_bonus": self.rare_bonus,
            "classic_bonus": self.classic_bonus,
            "hype_penalty": self.hype_penalty,
            "ugc_penalty": self.ugc_penalty,
            "strategy_modifier": self.strategy_modifier,
            "strategy": self.strategy_name,
            "base_score": self.base_score,
            "final_score": self.final_score,
        }


@dataclass
class ScoreResult:
    """Result of scoring an item."""

    item: Item
    listing_price: int
    score: int
    tier: ScoreTier
    breakdown: ScoreBreakdown
    discount_percent: float

    @property
    def should_auto_buy(self) -> bool:
        """Whether this score qualifies for auto-buy."""
        return self.tier in (ScoreTier.EXCELLENT, ScoreTier.GOOD)

    @property
    def should_alert(self) -> bool:
        """Whether this score qualifies for an alert."""
        return self.tier in (ScoreTier.EXCELLENT, ScoreTier.GOOD, ScoreTier.RISKY)

    def format_summary(self) -> str:
        """Format a summary string."""
        return (
            f"{self.item.name}: {self.score}/100 {self.tier.emoji} "
            f"({self.discount_percent:.1f}% off)"
        )


class SnipeScorer:
    """Multi-factor scoring algorithm for snipe opportunities.

    The algorithm evaluates items based on:
    1. DISCOUNT (0-30 points) - How far below value is the price?
    2. DEMAND (0-25 points) - How desirable is the item?
    3. TREND (0-20 points) - Is the value stable/rising?
    4. LIQUIDITY (0-15 points) - Can we resell quickly?
    5. STABILITY (0-10 points) - Does RAP match value?

    Plus bonuses/penalties for:
    - Rare items with high demand (+5)
    - Classic (non-UGC) items (+3)
    - Hyped items (-5)
    - UGC items (-3 to -10)

    Strategy flags apply additional modifiers to favor certain trade types.
    """

    # Base scoring weights
    DISCOUNT_WEIGHTS = {
        50: 30,  # 50%+ off = 30 points
        40: 25,  # 40-49% off = 25 points
        30: 20,  # 30-39% off = 20 points
        20: 10,  # 20-29% off = 10 points
    }

    DEMAND_SCORES = {
        Demand.AMAZING: 25,
        Demand.HIGH: 20,
        Demand.NORMAL: 12,
        Demand.LOW: 5,
        Demand.TERRIBLE: 0,
        Demand.NONE: 0,
    }

    TREND_SCORES = {
        Trend.RAISING: 20,
        Trend.STABLE: 15,
        Trend.FLUCTUATING: 8,
        Trend.UNSTABLE: 3,
        Trend.LOWERING: 0,
        Trend.NONE: 0,
    }

    def __init__(
        self,
        strategies: Optional[list[StrategyFlag]] = None,
        ugc_mode: Optional[UGCMode] = None,
    ) -> None:
        """Initialize scorer.

        Args:
            strategies: Strategy flags to apply. Uses config if None.
            ugc_mode: UGC handling mode. Uses config if None.
        """
        self.strategies = strategies or config.strategy_flags
        self.ugc_mode = ugc_mode or config.ugc_mode

    def score(self, item: Item, listing_price: int) -> ScoreResult:
        """Calculate snipe score for an item at a given price.

        Args:
            item: The item to score.
            listing_price: The current listing price.

        Returns:
            ScoreResult with score, tier, and breakdown.
        """
        breakdown = ScoreBreakdown()

        # Calculate discount percentage
        if item.value <= 0:
            discount_percent = 0.0
        else:
            discount_percent = (1 - listing_price / item.value) * 100

        # Minimum discount check (return 0 if not enough discount)
        if discount_percent < 20:
            return ScoreResult(
                item=item,
                listing_price=listing_price,
                score=0,
                tier=ScoreTier.REJECT,
                breakdown=breakdown,
                discount_percent=discount_percent,
            )

        # === DISCOUNT FACTOR (0-30 points) ===
        for threshold, points in sorted(
            self.DISCOUNT_WEIGHTS.items(), reverse=True
        ):
            if discount_percent >= threshold:
                breakdown.discount_score = points
                break

        # === DEMAND FACTOR (0-25 points) ===
        breakdown.demand_score = self.DEMAND_SCORES.get(item.demand, 0)

        # === TREND FACTOR (0-20 points) ===
        breakdown.trend_score = self.TREND_SCORES.get(item.trend, 0)

        # === LIQUIDITY FACTOR (0-15 points) ===
        if item.recent_sales_30d is not None:
            if item.recent_sales_30d >= 50:
                breakdown.liquidity_score = 15
            elif item.recent_sales_30d >= 20:
                breakdown.liquidity_score = 12
            elif item.recent_sales_30d >= 10:
                breakdown.liquidity_score = 8
            elif item.recent_sales_30d >= 5:
                breakdown.liquidity_score = 4
            else:
                breakdown.liquidity_score = 0
        else:
            # No sales data - assume moderate liquidity
            breakdown.liquidity_score = 6

        # === STABILITY FACTOR (0-10 points) ===
        if item.rap > 0 and item.value > 0:
            rap_value_ratio = item.rap / item.value
            if 0.85 <= rap_value_ratio <= 1.15:
                # RAP closely matches value - very stable
                breakdown.stability_score = 10
            elif 0.7 <= rap_value_ratio <= 1.3:
                # Moderate stability
                breakdown.stability_score = 5
            else:
                # RAP significantly different from value
                breakdown.stability_score = 0
        else:
            breakdown.stability_score = 0

        # === BONUSES ===
        # Rare + High demand bonus
        if item.rare and item.demand >= Demand.HIGH:
            breakdown.rare_bonus = 5

        # Classic (non-UGC) bonus
        if not item.is_ugc:
            breakdown.classic_bonus = 3

        # === PENALTIES ===
        # Hyped item penalty
        if item.hyped:
            breakdown.hype_penalty = -5

        # UGC penalty (if included)
        if item.is_ugc and self.ugc_mode == UGCMode.INCLUDE:
            breakdown.ugc_penalty = -10

        # Calculate base score before strategy modifiers
        breakdown.base_score = (
            breakdown.discount_score
            + breakdown.demand_score
            + breakdown.trend_score
            + breakdown.liquidity_score
            + breakdown.stability_score
            + breakdown.rare_bonus
            + breakdown.classic_bonus
            + breakdown.hype_penalty
            + breakdown.ugc_penalty
        )

        # === STRATEGY MODIFIERS ===
        strategy_mod = self._calculate_strategy_modifier(
            item, listing_price, discount_percent, breakdown
        )
        breakdown.strategy_modifier = strategy_mod
        breakdown.strategy_name = ", ".join(s.value for s in self.strategies)

        # Final score (clamped to 0-100)
        breakdown.final_score = max(0, min(100, breakdown.base_score + strategy_mod))

        return ScoreResult(
            item=item,
            listing_price=listing_price,
            score=breakdown.final_score,
            tier=ScoreTier.from_score(breakdown.final_score),
            breakdown=breakdown,
            discount_percent=discount_percent,
        )

    def _calculate_strategy_modifier(
        self,
        item: Item,
        listing_price: int,
        discount_percent: float,
        breakdown: ScoreBreakdown,
    ) -> int:
        """Calculate strategy-based score modifiers.

        Args:
            item: The item being scored.
            listing_price: Current listing price.
            discount_percent: Calculated discount percentage.
            breakdown: Current score breakdown.

        Returns:
            Total modifier from all active strategies.
        """
        modifier = 0

        for strategy in self.strategies:
            if strategy == StrategyFlag.QUICK_FLIPS:
                # Quick Flips: Favor high liquidity
                # +15 if excellent liquidity, -10 if poor
                if item.recent_sales_30d is not None:
                    if item.recent_sales_30d >= 20:
                        modifier += 15
                    elif item.recent_sales_30d < 5:
                        modifier -= 10

            elif strategy == StrategyFlag.VALUE_PLAYS:
                # Value Plays: Favor deep discounts + stability
                # +20 if 40%+ off AND stable trend
                if discount_percent >= 40 and item.trend == Trend.STABLE:
                    modifier += 20
                elif discount_percent >= 40:
                    modifier += 10

            elif strategy == StrategyFlag.RARE_HUNTING:
                # Rare Hunting: Big bonus for rare items with demand
                # +25 if rare AND demand >= High
                if item.rare and item.demand >= Demand.HIGH:
                    modifier += 25
                elif item.rare and item.demand >= Demand.NORMAL:
                    modifier += 15
                # Penalty if not rare (wrong strategy)
                elif not item.rare:
                    modifier -= 5

        return modifier

    def score_batch(
        self, items_with_prices: list[tuple[Item, int]]
    ) -> list[ScoreResult]:
        """Score multiple items at once.

        Args:
            items_with_prices: List of (Item, listing_price) tuples.

        Returns:
            List of ScoreResults sorted by score (highest first).
        """
        results = [self.score(item, price) for item, price in items_with_prices]
        return sorted(results, key=lambda r: r.score, reverse=True)

    def get_best_opportunities(
        self,
        items_with_prices: list[tuple[Item, int]],
        min_tier: ScoreTier = ScoreTier.RISKY,
        limit: int = 10,
    ) -> list[ScoreResult]:
        """Get the best snipe opportunities from a batch.

        Args:
            items_with_prices: List of (Item, listing_price) tuples.
            min_tier: Minimum tier to include.
            limit: Maximum results to return.

        Returns:
            Top scoring items that meet the tier threshold.
        """
        results = self.score_batch(items_with_prices)

        # Filter by tier
        tier_order = [ScoreTier.EXCELLENT, ScoreTier.GOOD, ScoreTier.RISKY, ScoreTier.REJECT]
        min_tier_idx = tier_order.index(min_tier)
        filtered = [r for r in results if tier_order.index(r.tier) <= min_tier_idx]

        return filtered[:limit]
