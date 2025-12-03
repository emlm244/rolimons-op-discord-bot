"""Sniper engine - the main polling loop that finds and acts on opportunities."""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Callable, Optional, Awaitable

from src.config import config, PurchaseMode
from src.data.rolimons_client import RolimonsClient
from src.data.roblox_client import RobloxClient, PurchaseResult
from src.data.models import Item, Listing, Deal
from src.analysis.filters import PreFilter, FilterResult
from src.sniper.scorer import SnipeScorer, ScoreResult, ScoreTier

logger = logging.getLogger(__name__)


class EngineState(Enum):
    """Sniper engine states."""

    STOPPED = "stopped"
    STARTING = "starting"
    RUNNING = "running"
    STOPPING = "stopping"
    PAUSED = "paused"
    ERROR = "error"


@dataclass
class EngineStats:
    """Statistics for the sniper engine."""

    started_at: Optional[datetime] = None
    items_scanned: int = 0
    items_filtered: int = 0
    items_scored: int = 0
    opportunities_found: int = 0
    purchases_attempted: int = 0
    purchases_successful: int = 0
    total_spent: int = 0
    last_scan_at: Optional[datetime] = None
    errors: int = 0


@dataclass
class Opportunity:
    """A detected snipe opportunity."""

    score_result: ScoreResult
    listing: Listing
    detected_at: datetime = field(default_factory=datetime.utcnow)

    @property
    def item(self) -> Item:
        return self.score_result.item

    @property
    def score(self) -> int:
        return self.score_result.score

    @property
    def tier(self) -> ScoreTier:
        return self.score_result.tier


# Callback types
OnOpportunityCallback = Callable[[Opportunity], Awaitable[None]]
OnPurchaseCallback = Callable[[Opportunity, PurchaseResult], Awaitable[None]]


class SniperEngine:
    """Main sniper engine that polls for deals and acts on opportunities.

    The engine:
    1. Fetches item data from Rolimons
    2. Fetches reseller listings from Roblox
    3. Runs items through pre-filters
    4. Scores passing items with the algorithm
    5. Based on purchase mode, either auto-buys or alerts

    Callbacks allow the Discord bot to receive notifications.
    """

    def __init__(
        self,
        rolimons: Optional[RolimonsClient] = None,
        roblox: Optional[RobloxClient] = None,
        pre_filter: Optional[PreFilter] = None,
        scorer: Optional[SnipeScorer] = None,
    ) -> None:
        """Initialize the sniper engine.

        Args:
            rolimons: Rolimons API client.
            roblox: Roblox API client.
            pre_filter: Pre-filter instance.
            scorer: Scorer instance.
        """
        self.rolimons = rolimons or RolimonsClient()
        self.roblox = roblox or RobloxClient()
        self.pre_filter = pre_filter or PreFilter()
        self.scorer = scorer or SnipeScorer()

        self.state = EngineState.STOPPED
        self.stats = EngineStats()

        self._task: Optional[asyncio.Task] = None
        self._stop_event = asyncio.Event()

        # Callbacks
        self._on_opportunity: Optional[OnOpportunityCallback] = None
        self._on_purchase: Optional[OnPurchaseCallback] = None

        # Track items we've already alerted on (to avoid spam)
        self._alerted_items: set[tuple[int, int]] = set()  # (item_id, price)

        # Purchase mode
        self.purchase_mode = config.purchase_mode

        # Budget tracking
        self._session_spent = 0
        self._purchases_this_hour: list[datetime] = []

    def on_opportunity(self, callback: OnOpportunityCallback) -> None:
        """Register callback for when an opportunity is found."""
        self._on_opportunity = callback

    def on_purchase(self, callback: OnPurchaseCallback) -> None:
        """Register callback for purchase results."""
        self._on_purchase = callback

    async def start(self) -> None:
        """Start the sniper engine."""
        if self.state in (EngineState.RUNNING, EngineState.STARTING):
            logger.warning("Engine already running")
            return

        logger.info("Starting sniper engine...")
        self.state = EngineState.STARTING
        self._stop_event.clear()
        self.stats = EngineStats(started_at=datetime.utcnow())

        self._task = asyncio.create_task(self._run_loop())
        self.state = EngineState.RUNNING
        logger.info("Sniper engine started")

    async def stop(self) -> None:
        """Stop the sniper engine."""
        if self.state == EngineState.STOPPED:
            return

        logger.info("Stopping sniper engine...")
        self.state = EngineState.STOPPING
        self._stop_event.set()

        if self._task:
            try:
                await asyncio.wait_for(self._task, timeout=10.0)
            except asyncio.TimeoutError:
                self._task.cancel()
                try:
                    await self._task
                except asyncio.CancelledError:
                    pass

        self.state = EngineState.STOPPED
        logger.info("Sniper engine stopped")

    async def pause(self) -> None:
        """Pause the engine (stops scanning but doesn't reset stats)."""
        if self.state == EngineState.RUNNING:
            self.state = EngineState.PAUSED
            logger.info("Sniper engine paused")

    async def resume(self) -> None:
        """Resume a paused engine."""
        if self.state == EngineState.PAUSED:
            self.state = EngineState.RUNNING
            logger.info("Sniper engine resumed")

    async def _run_loop(self) -> None:
        """Main sniper loop."""
        while not self._stop_event.is_set():
            if self.state == EngineState.PAUSED:
                await asyncio.sleep(1)
                continue

            try:
                await self._scan_for_opportunities()
            except Exception as e:
                logger.error(f"Error in sniper loop: {e}", exc_info=True)
                self.stats.errors += 1

            # Wait for next poll interval
            try:
                await asyncio.wait_for(
                    self._stop_event.wait(),
                    timeout=config.poll_interval_seconds,
                )
                break  # Stop event was set
            except asyncio.TimeoutError:
                pass  # Normal timeout, continue loop

    async def _scan_for_opportunities(self) -> None:
        """Perform one scan cycle."""
        logger.debug("Starting scan cycle...")
        self.stats.last_scan_at = datetime.utcnow()

        # 1. Get all items from Rolimons
        items = await self.rolimons.get_all_items()
        self.stats.items_scanned += len(items)

        # 2. For items with good potential, fetch reseller listings
        # Focus on items with good demand and value
        candidates = [
            item for item in items.values()
            if item.demand >= 2  # Normal or better
            and item.value > 0
            and not item.projected
        ]

        opportunities = []

        for item in candidates[:50]:  # Limit to avoid rate limits
            # Fetch reseller listings
            listings = await self.roblox.get_resellers(item.item_id, limit=5)

            if not listings:
                continue

            # Check each listing
            for listing in listings:
                # Skip if already alerted
                alert_key = (item.item_id, listing.price)
                if alert_key in self._alerted_items:
                    continue

                # Run pre-filter
                filter_result = self.pre_filter.filter(item, listing.price)
                self.stats.items_filtered += 1

                if not filter_result.passed:
                    continue

                # Score the opportunity
                score_result = self.scorer.score(item, listing.price)
                self.stats.items_scored += 1

                if score_result.tier == ScoreTier.REJECT:
                    continue

                # Create opportunity
                opportunity = Opportunity(
                    score_result=score_result,
                    listing=listing,
                )
                opportunities.append(opportunity)
                self._alerted_items.add(alert_key)
                self.stats.opportunities_found += 1

            # Small delay between items to avoid rate limits
            await asyncio.sleep(0.5)

        # 3. Process opportunities based on purchase mode
        for opportunity in sorted(opportunities, key=lambda o: o.score, reverse=True):
            await self._handle_opportunity(opportunity)

        logger.debug(f"Scan complete. Found {len(opportunities)} opportunities")

    async def _handle_opportunity(self, opportunity: Opportunity) -> None:
        """Handle a detected opportunity based on purchase mode."""

        # Notify via callback
        if self._on_opportunity:
            try:
                await self._on_opportunity(opportunity)
            except Exception as e:
                logger.error(f"Error in opportunity callback: {e}")

        # Check if we should auto-buy
        should_buy = False

        if self.purchase_mode == PurchaseMode.FULL_AUTO:
            # Auto-buy anything that meets threshold
            should_buy = opportunity.score >= config.snipe_threshold

        elif self.purchase_mode == PurchaseMode.HYBRID:
            # Only auto-buy excellent tier
            should_buy = opportunity.tier == ScoreTier.EXCELLENT

        elif self.purchase_mode == PurchaseMode.ALERT_CONFIRM:
            # Never auto-buy, just alert
            should_buy = False

        if should_buy:
            await self._execute_purchase(opportunity)

    async def _execute_purchase(self, opportunity: Opportunity) -> None:
        """Execute a purchase for an opportunity."""

        # Budget checks
        if not self._check_budget(opportunity.listing.price):
            logger.info(f"Skipping purchase - budget exceeded")
            return

        # Rate limit check
        if not self._check_purchase_rate():
            logger.info(f"Skipping purchase - rate limit")
            return

        logger.info(
            f"Executing purchase: {opportunity.item.name} "
            f"for {opportunity.listing.price} R$"
        )

        self.stats.purchases_attempted += 1

        # Execute purchase
        result = await self.roblox.purchase(
            product_id=opportunity.listing.product_id,
            expected_price=opportunity.listing.price,
            expected_seller_id=opportunity.listing.seller_id,
            user_asset_id=opportunity.listing.user_asset_id,
        )

        if result.result == PurchaseResult.SUCCESS:
            self.stats.purchases_successful += 1
            self._session_spent += opportunity.listing.price
            self.stats.total_spent += opportunity.listing.price
            self._purchases_this_hour.append(datetime.utcnow())
            logger.info(f"Purchase successful!")
        else:
            logger.warning(f"Purchase failed: {result.message}")

        # Notify via callback
        if self._on_purchase:
            try:
                await self._on_purchase(opportunity, result.result)
            except Exception as e:
                logger.error(f"Error in purchase callback: {e}")

    def _check_budget(self, price: int) -> bool:
        """Check if purchase is within budget."""
        if price > config.max_price_per_item:
            return False
        if self._session_spent + price > config.total_budget:
            return False
        return True

    def _check_purchase_rate(self) -> bool:
        """Check if we're within purchase rate limit."""
        now = datetime.utcnow()
        hour_ago = now.replace(hour=now.hour - 1 if now.hour > 0 else 23)

        # Remove old entries
        self._purchases_this_hour = [
            t for t in self._purchases_this_hour if t > hour_ago
        ]

        return len(self._purchases_this_hour) < config.max_purchases_per_hour

    async def manual_purchase(self, opportunity: Opportunity) -> PurchaseResult:
        """Manually trigger a purchase (for confirm button).

        Returns:
            The actual PurchaseResult from the Roblox API.
        """
        # Budget checks
        if not self._check_budget(opportunity.listing.price):
            return PurchaseResult.INSUFFICIENT_FUNDS

        # Rate limit check
        if not self._check_purchase_rate():
            return PurchaseResult.RATE_LIMITED

        self.stats.purchases_attempted += 1

        # Execute purchase and return actual result
        result = await self.roblox.purchase(
            product_id=opportunity.listing.product_id,
            expected_price=opportunity.listing.price,
            expected_seller_id=opportunity.listing.seller_id,
            user_asset_id=opportunity.listing.user_asset_id,
        )

        if result.result == PurchaseResult.SUCCESS:
            self.stats.purchases_successful += 1
            self._session_spent += opportunity.listing.price
            self.stats.total_spent += opportunity.listing.price
            self._purchases_this_hour.append(datetime.utcnow())

        # Notify via callback
        if self._on_purchase:
            try:
                await self._on_purchase(opportunity, result.result)
            except Exception as e:
                logger.error(f"Error in purchase callback: {e}")

        return result.result

    def get_status(self) -> dict:
        """Get current engine status."""
        return {
            "state": self.state.value,
            "stats": {
                "started_at": self.stats.started_at.isoformat() if self.stats.started_at else None,
                "items_scanned": self.stats.items_scanned,
                "items_filtered": self.stats.items_filtered,
                "items_scored": self.stats.items_scored,
                "opportunities_found": self.stats.opportunities_found,
                "purchases_attempted": self.stats.purchases_attempted,
                "purchases_successful": self.stats.purchases_successful,
                "total_spent": self.stats.total_spent,
                "last_scan_at": self.stats.last_scan_at.isoformat() if self.stats.last_scan_at else None,
                "errors": self.stats.errors,
            },
            "config": {
                "purchase_mode": self.purchase_mode.value,
                "poll_interval": config.poll_interval_seconds,
                "snipe_threshold": config.snipe_threshold,
                "max_price_per_item": config.max_price_per_item,
                "total_budget": config.total_budget,
            },
        }

    async def close(self) -> None:
        """Clean up resources."""
        await self.stop()
        await self.rolimons.close()
        await self.roblox.close()
