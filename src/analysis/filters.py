"""Pre-filters for rejecting items before scoring.

These filters implement hard rejection rules - items that should NEVER
be sniped regardless of price. This prevents the algorithm from wasting
time scoring obviously bad deals.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Optional

from src.config import config, UGCMode
from src.data.models import Item, Demand, Trend


class RejectReason(Enum):
    """Reasons why an item was rejected by pre-filters."""

    PASSED = "passed"  # Not rejected
    PROJECTED = "projected"
    TERRIBLE_DEMAND = "terrible_demand"
    NO_DEMAND = "no_demand"
    LOWERING_TREND = "lowering_trend"
    UGC_EXCLUDED = "ugc_excluded"
    UGC_TOO_NEW = "ugc_too_new"
    TOO_ILLIQUID = "too_illiquid"
    NO_SALES = "no_sales"
    NO_VALUE = "no_value"
    PRICE_TOO_HIGH = "price_too_high"
    INSUFFICIENT_DISCOUNT = "insufficient_discount"

    @property
    def description(self) -> str:
        """Human-readable description of rejection reason."""
        descriptions = {
            "passed": "Item passed all filters",
            "projected": "Item is marked as projected (artificially inflated RAP)",
            "terrible_demand": "Item has terrible demand rating",
            "no_demand": "Item has no demand data",
            "lowering_trend": "Item trend is actively lowering",
            "ugc_excluded": "UGC items are excluded by configuration",
            "ugc_too_new": "UGC item is too new (< 30 days old)",
            "too_illiquid": "Item has too few copies remaining (< 5)",
            "no_sales": "Item has no recent sales (90+ days)",
            "no_value": "Item has no Rolimons value assigned",
            "price_too_high": "Price exceeds maximum budget",
            "insufficient_discount": "Discount is below minimum threshold",
        }
        return descriptions.get(self.value, "Unknown reason")


@dataclass
class FilterResult:
    """Result of running pre-filters on an item."""

    passed: bool
    reason: RejectReason
    item: Item
    listing_price: Optional[int] = None
    discount_percent: Optional[float] = None

    @property
    def message(self) -> str:
        """Get a formatted message about the filter result."""
        if self.passed:
            return f"[PASS] {self.item.name}"
        return f"[REJECT] {self.item.name}: {self.reason.description}"


class PreFilter:
    """Pre-filter system for rejecting items before scoring.

    Implements hard rejection rules based on:
    - Projected status (never buy projected items)
    - Demand level (reject terrible/no demand)
    - Trend (reject actively lowering)
    - UGC rules (configurable)
    - Liquidity (reject illiquid items)
    - Budget limits
    """

    def __init__(
        self,
        ugc_mode: Optional[UGCMode] = None,
        min_discount: float = 20.0,
        max_price: Optional[int] = None,
        min_copies: int = 5,
        max_days_no_sales: int = 90,
        min_ugc_age_days: int = 30,
    ) -> None:
        """Initialize pre-filter.

        Args:
            ugc_mode: How to handle UGC items. Uses config if None.
            min_discount: Minimum discount percentage to consider.
            max_price: Maximum price to pay (uses config if None).
            min_copies: Minimum copies remaining for liquidity.
            max_days_no_sales: Max days without sales before rejection.
            min_ugc_age_days: Minimum age for UGC items.
        """
        self.ugc_mode = ugc_mode or config.ugc_mode
        self.min_discount = min_discount
        self.max_price = max_price or config.max_price_per_item
        self.min_copies = min_copies
        self.max_days_no_sales = max_days_no_sales
        self.min_ugc_age_days = min_ugc_age_days

    def filter(self, item: Item, listing_price: int) -> FilterResult:
        """Run all pre-filters on an item.

        Args:
            item: The item to filter.
            listing_price: The current listing price.

        Returns:
            FilterResult indicating pass/fail and reason.
        """
        # Calculate discount
        discount_percent = 0.0
        if item.value > 0:
            discount_percent = (1 - listing_price / item.value) * 100

        # Create base result
        base_result = FilterResult(
            passed=False,
            reason=RejectReason.PASSED,
            item=item,
            listing_price=listing_price,
            discount_percent=discount_percent,
        )

        # Run filters in order of importance/speed

        # 1. PROJECTED - Never buy projected items
        if item.projected:
            return FilterResult(
                passed=False,
                reason=RejectReason.PROJECTED,
                item=item,
                listing_price=listing_price,
                discount_percent=discount_percent,
            )

        # 2. NO VALUE - Can't calculate discount without value
        if item.value <= 0:
            return FilterResult(
                passed=False,
                reason=RejectReason.NO_VALUE,
                item=item,
                listing_price=listing_price,
                discount_percent=discount_percent,
            )

        # 3. DEMAND - Reject terrible or no demand
        if item.demand == Demand.NONE:
            return FilterResult(
                passed=False,
                reason=RejectReason.NO_DEMAND,
                item=item,
                listing_price=listing_price,
                discount_percent=discount_percent,
            )

        if item.demand == Demand.TERRIBLE:
            return FilterResult(
                passed=False,
                reason=RejectReason.TERRIBLE_DEMAND,
                item=item,
                listing_price=listing_price,
                discount_percent=discount_percent,
            )

        # 4. TREND - Reject actively lowering trend
        if item.trend == Trend.LOWERING:
            return FilterResult(
                passed=False,
                reason=RejectReason.LOWERING_TREND,
                item=item,
                listing_price=listing_price,
                discount_percent=discount_percent,
            )

        # 5. UGC RULES
        if item.is_ugc:
            if self.ugc_mode == UGCMode.EXCLUDE:
                return FilterResult(
                    passed=False,
                    reason=RejectReason.UGC_EXCLUDED,
                    item=item,
                    listing_price=listing_price,
                    discount_percent=discount_percent,
                )

            # Check UGC age
            if item.created_at:
                age_days = (datetime.utcnow() - item.created_at).days
                if age_days < self.min_ugc_age_days:
                    return FilterResult(
                        passed=False,
                        reason=RejectReason.UGC_TOO_NEW,
                        item=item,
                        listing_price=listing_price,
                        discount_percent=discount_percent,
                    )

        # 6. LIQUIDITY - Check copies remaining
        if item.copies_remaining is not None and item.copies_remaining < self.min_copies:
            return FilterResult(
                passed=False,
                reason=RejectReason.TOO_ILLIQUID,
                item=item,
                listing_price=listing_price,
                discount_percent=discount_percent,
            )

        # 7. SALES - Check recent sales (if data available)
        if item.recent_sales_30d is not None and item.recent_sales_30d == 0:
            # No sales in 30 days - likely dead item
            return FilterResult(
                passed=False,
                reason=RejectReason.NO_SALES,
                item=item,
                listing_price=listing_price,
                discount_percent=discount_percent,
            )

        # 8. PRICE - Check against max budget
        if listing_price > self.max_price:
            return FilterResult(
                passed=False,
                reason=RejectReason.PRICE_TOO_HIGH,
                item=item,
                listing_price=listing_price,
                discount_percent=discount_percent,
            )

        # 9. DISCOUNT - Check minimum discount threshold
        if discount_percent < self.min_discount:
            return FilterResult(
                passed=False,
                reason=RejectReason.INSUFFICIENT_DISCOUNT,
                item=item,
                listing_price=listing_price,
                discount_percent=discount_percent,
            )

        # All filters passed!
        return FilterResult(
            passed=True,
            reason=RejectReason.PASSED,
            item=item,
            listing_price=listing_price,
            discount_percent=discount_percent,
        )

    def filter_batch(
        self, items_with_prices: list[tuple[Item, int]]
    ) -> tuple[list[FilterResult], list[FilterResult]]:
        """Filter multiple items at once.

        Args:
            items_with_prices: List of (Item, listing_price) tuples.

        Returns:
            Tuple of (passed_results, rejected_results).
        """
        passed = []
        rejected = []

        for item, price in items_with_prices:
            result = self.filter(item, price)
            if result.passed:
                passed.append(result)
            else:
                rejected.append(result)

        return passed, rejected
