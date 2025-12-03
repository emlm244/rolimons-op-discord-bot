"""Purchase executor with safety checks and logging."""

from __future__ import annotations

import asyncio
import logging
import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from src.config import config
from src.data.roblox_client import RobloxClient, PurchaseResult, PurchaseResponse
from src.data.models import Item, Listing, PurchaseRecord
from src.sniper.scorer import ScoreResult

logger = logging.getLogger(__name__)


@dataclass
class ExecutionResult:
    """Result of a purchase execution attempt."""

    success: bool
    purchase_result: PurchaseResult
    message: str
    record: Optional[PurchaseRecord] = None
    response: Optional[PurchaseResponse] = None


class PurchaseExecutor:
    """Handles purchase execution with safety checks, cooldowns, and logging.

    Safety features:
    - Budget enforcement (per-item and total)
    - Purchase rate limiting
    - Cooldown between purchases
    - Listing verification before purchase
    - Detailed logging
    """

    def __init__(
        self,
        roblox_client: Optional[RobloxClient] = None,
    ) -> None:
        """Initialize executor.

        Args:
            roblox_client: Roblox API client.
        """
        self.roblox = roblox_client or RobloxClient()

        # Tracking
        self._session_spent = 0
        self._purchase_times: list[datetime] = []
        self._last_purchase_time: Optional[datetime] = None
        self._purchase_records: list[PurchaseRecord] = []

    async def execute(
        self,
        item: Item,
        listing: Listing,
        score_result: ScoreResult,
        strategy: str = "",
    ) -> ExecutionResult:
        """Execute a purchase with full safety checks.

        Args:
            item: The item to purchase.
            listing: The listing to buy from.
            score_result: The score result that triggered this purchase.
            strategy: The strategy that was used.

        Returns:
            ExecutionResult with success status and details.
        """
        # === SAFETY CHECK 1: Budget ===
        if listing.price > config.max_price_per_item:
            return ExecutionResult(
                success=False,
                purchase_result=PurchaseResult.UNKNOWN_ERROR,
                message=f"Price {listing.price} exceeds max per-item budget {config.max_price_per_item}",
            )

        if self._session_spent + listing.price > config.total_budget:
            return ExecutionResult(
                success=False,
                purchase_result=PurchaseResult.INSUFFICIENT_FUNDS,
                message=f"Purchase would exceed total budget. Spent: {self._session_spent}, Budget: {config.total_budget}",
            )

        # === SAFETY CHECK 2: Rate Limit ===
        if not self._check_rate_limit():
            return ExecutionResult(
                success=False,
                purchase_result=PurchaseResult.RATE_LIMITED,
                message=f"Purchase rate limit exceeded ({config.max_purchases_per_hour}/hour)",
            )

        # === SAFETY CHECK 3: Cooldown ===
        if not self._check_cooldown():
            return ExecutionResult(
                success=False,
                purchase_result=PurchaseResult.RATE_LIMITED,
                message=f"Cooldown active. Wait {config.cooldown_between_purchases}s between purchases",
            )

        # === SAFETY CHECK 4: Verify Listing Still Exists ===
        current_listings = await self.roblox.get_resellers(item.item_id, limit=10)
        listing_exists = any(
            l.product_id == listing.product_id and l.price == listing.price
            for l in current_listings
        )

        if not listing_exists:
            return ExecutionResult(
                success=False,
                purchase_result=PurchaseResult.LISTING_GONE,
                message="Listing no longer available at expected price",
            )

        # === EXECUTE PURCHASE ===
        logger.info(
            f"Executing purchase: {item.name} ({item.item_id}) "
            f"for {listing.price} R$ from {listing.seller_name}"
        )

        response = await self.roblox.purchase(
            product_id=listing.product_id,
            expected_price=listing.price,
            expected_seller_id=listing.seller_id,
            user_asset_id=listing.user_asset_id,
        )

        # Create purchase record
        record = PurchaseRecord(
            record_id=str(uuid.uuid4()),
            item_id=item.item_id,
            item_name=item.name,
            purchase_price=listing.price,
            purchase_time=datetime.utcnow(),
            seller_id=listing.seller_id,
            snipe_score=score_result.score,
            strategy_used=strategy,
            success=response.result == PurchaseResult.SUCCESS,
            error_message=None if response.result == PurchaseResult.SUCCESS else response.message,
            current_value=item.value,
            current_rap=item.rap,
        )

        if response.result == PurchaseResult.SUCCESS:
            # Update tracking
            self._session_spent += listing.price
            self._purchase_times.append(datetime.utcnow())
            self._last_purchase_time = datetime.utcnow()
            self._purchase_records.append(record)

            logger.info(
                f"Purchase successful! {item.name} for {listing.price} R$ "
                f"(Score: {score_result.score}, Discount: {score_result.discount_percent:.1f}%)"
            )

            return ExecutionResult(
                success=True,
                purchase_result=PurchaseResult.SUCCESS,
                message=f"Successfully purchased {item.name} for {listing.price} R$",
                record=record,
                response=response,
            )
        else:
            self._purchase_records.append(record)

            logger.warning(
                f"Purchase failed: {response.message} "
                f"(Item: {item.name}, Price: {listing.price})"
            )

            return ExecutionResult(
                success=False,
                purchase_result=response.result,
                message=response.message,
                record=record,
                response=response,
            )

    def _check_rate_limit(self) -> bool:
        """Check if we're within hourly purchase limit."""
        now = datetime.utcnow()
        one_hour_ago = datetime(
            now.year, now.month, now.day,
            now.hour - 1 if now.hour > 0 else 23,
            now.minute, now.second,
        )

        # Count purchases in last hour
        recent = [t for t in self._purchase_times if t > one_hour_ago]
        self._purchase_times = recent  # Clean up old entries

        return len(recent) < config.max_purchases_per_hour

    def _check_cooldown(self) -> bool:
        """Check if cooldown period has passed since last purchase."""
        if self._last_purchase_time is None:
            return True

        elapsed = (datetime.utcnow() - self._last_purchase_time).total_seconds()
        return elapsed >= config.cooldown_between_purchases

    @property
    def session_spent(self) -> int:
        """Total Robux spent this session."""
        return self._session_spent

    @property
    def remaining_budget(self) -> int:
        """Remaining budget for this session."""
        return config.total_budget - self._session_spent

    @property
    def purchases_this_hour(self) -> int:
        """Number of purchases in the last hour."""
        now = datetime.utcnow()
        one_hour_ago = datetime(
            now.year, now.month, now.day,
            now.hour - 1 if now.hour > 0 else 23,
            now.minute, now.second,
        )
        return len([t for t in self._purchase_times if t > one_hour_ago])

    @property
    def seconds_until_cooldown_expires(self) -> float:
        """Seconds until cooldown expires."""
        if self._last_purchase_time is None:
            return 0

        elapsed = (datetime.utcnow() - self._last_purchase_time).total_seconds()
        remaining = config.cooldown_between_purchases - elapsed
        return max(0, remaining)

    def get_purchase_records(self) -> list[PurchaseRecord]:
        """Get all purchase records from this session."""
        return self._purchase_records.copy()

    def get_successful_purchases(self) -> list[PurchaseRecord]:
        """Get only successful purchase records."""
        return [r for r in self._purchase_records if r.success]

    def get_failed_purchases(self) -> list[PurchaseRecord]:
        """Get only failed purchase records."""
        return [r for r in self._purchase_records if not r.success]

    def reset_session(self) -> None:
        """Reset session tracking (keep records)."""
        self._session_spent = 0
        self._purchase_times = []
        self._last_purchase_time = None

    def get_status(self) -> dict:
        """Get executor status."""
        return {
            "session_spent": self._session_spent,
            "remaining_budget": self.remaining_budget,
            "purchases_this_hour": self.purchases_this_hour,
            "cooldown_remaining": self.seconds_until_cooldown_expires,
            "total_purchases": len(self._purchase_records),
            "successful_purchases": len(self.get_successful_purchases()),
            "failed_purchases": len(self.get_failed_purchases()),
        }
