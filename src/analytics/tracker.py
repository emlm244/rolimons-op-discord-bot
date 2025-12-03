"""Analytics tracker for real-time P&L updates."""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime
from typing import Optional

from src.config import config
from src.data.rolimons_client import RolimonsClient
from src.data.models import PurchaseRecord, PortfolioStats
from src.analytics.storage import AnalyticsStorage

logger = logging.getLogger(__name__)


class AnalyticsTracker:
    """Tracks portfolio performance and updates values periodically."""

    def __init__(
        self,
        storage: Optional[AnalyticsStorage] = None,
        rolimons: Optional[RolimonsClient] = None,
        update_interval: int = 300,  # 5 minutes
    ) -> None:
        """Initialize tracker.

        Args:
            storage: Analytics storage instance.
            rolimons: Rolimons client for value lookups.
            update_interval: Seconds between value updates.
        """
        self.storage = storage or AnalyticsStorage()
        self.rolimons = rolimons or RolimonsClient()
        self.update_interval = update_interval

        self._running = False
        self._task: Optional[asyncio.Task] = None

    async def start(self) -> None:
        """Start the background update task."""
        if self._running:
            return

        self._running = True
        self._task = asyncio.create_task(self._update_loop())
        logger.info("Analytics tracker started")

    async def stop(self) -> None:
        """Stop the background update task."""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("Analytics tracker stopped")

    async def _update_loop(self) -> None:
        """Background loop to update values."""
        while self._running:
            try:
                await self._update_values()
            except Exception as e:
                logger.error(f"Error updating values: {e}")

            await asyncio.sleep(self.update_interval)

    async def _update_values(self) -> None:
        """Update current values for all held items."""
        purchases = self.storage.get_successful_purchases()

        # Filter to unsold items
        held_items = [p for p in purchases if p.sold_price is None]

        if not held_items:
            return

        # Get current item data
        items = await self.rolimons.get_all_items()

        updated = 0
        for record in held_items:
            item = items.get(record.item_id)
            if item:
                old_value = record.current_value
                record.current_value = item.value
                record.current_rap = item.rap

                if old_value != item.value:
                    updated += 1
                    self.storage.update_purchase(
                        record.record_id,
                        current_value=item.value,
                        current_rap=item.rap,
                    )

        if updated > 0:
            logger.info(f"Updated values for {updated} items")

    def record_purchase(self, record: PurchaseRecord) -> None:
        """Record a new purchase."""
        self.storage.add_purchase(record)

    def record_sale(
        self, record_id: str, sold_price: int, sold_time: Optional[datetime] = None
    ) -> bool:
        """Record a sale."""
        return self.storage.mark_sold(record_id, sold_price, sold_time)

    def get_portfolio_stats(self) -> PortfolioStats:
        """Get current portfolio statistics."""
        return self.storage.calculate_stats()

    def get_all_purchases(self) -> list[PurchaseRecord]:
        """Get all purchase records."""
        return self.storage.get_all_purchases()

    def get_best_snipes(self, limit: int = 5) -> list[PurchaseRecord]:
        """Get best performing snipes."""
        return self.storage.get_best_snipes(limit)

    def get_worst_snipes(self, limit: int = 5) -> list[PurchaseRecord]:
        """Get worst performing snipes."""
        return self.storage.get_worst_snipes(limit)

    def get_stats_by_strategy(self) -> dict[str, PortfolioStats]:
        """Get stats grouped by strategy."""
        return self.storage.get_stats_by_strategy()

    def get_summary(self) -> dict:
        """Get a summary of analytics."""
        stats = self.get_portfolio_stats()
        by_strategy = self.get_stats_by_strategy()

        return {
            "portfolio": {
                "total_spent": stats.total_spent,
                "current_value": stats.current_value,
                "unrealized_pnl": stats.unrealized_pnl,
                "unrealized_pnl_percent": stats.unrealized_pnl_percent,
                "realized_pnl": stats.realized_pnl,
            },
            "performance": {
                "total_purchases": stats.total_purchases,
                "successful_purchases": stats.successful_purchases,
                "failed_purchases": stats.failed_purchases,
                "win_rate": stats.win_rate,
                "success_rate": stats.success_rate,
            },
            "by_strategy": {
                name: {
                    "trades": s.total_purchases,
                    "spent": s.total_spent,
                    "pnl": s.unrealized_pnl,
                    "pnl_percent": s.unrealized_pnl_percent,
                }
                for name, s in by_strategy.items()
            },
        }

    async def close(self) -> None:
        """Clean up resources."""
        await self.stop()
        await self.rolimons.close()
