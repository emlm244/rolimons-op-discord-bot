"""JSON-based storage for analytics data."""

from __future__ import annotations

import json
import logging
import os
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import Optional

from src.config import config
from src.data.models import PurchaseRecord, PortfolioStats

logger = logging.getLogger(__name__)


class AnalyticsStorage:
    """Persistent storage for purchase records and analytics."""

    def __init__(self, data_dir: Optional[str] = None) -> None:
        """Initialize storage.

        Args:
            data_dir: Directory for data files. Uses config if None.
        """
        self.data_dir = Path(data_dir or config.data_dir)
        self.purchases_file = self.data_dir / "purchases.json"
        self.stats_file = self.data_dir / "stats.json"

        # Ensure data directory exists
        self.data_dir.mkdir(parents=True, exist_ok=True)

        # Load existing data
        self._purchases: list[PurchaseRecord] = []
        self._load_purchases()

    def _load_purchases(self) -> None:
        """Load purchases from disk."""
        if not self.purchases_file.exists():
            return

        try:
            with open(self.purchases_file, "r") as f:
                data = json.load(f)

            self._purchases = []
            for item in data:
                # Convert datetime strings back to datetime objects
                if item.get("purchase_time"):
                    item["purchase_time"] = datetime.fromisoformat(item["purchase_time"])
                if item.get("sold_time"):
                    item["sold_time"] = datetime.fromisoformat(item["sold_time"])

                self._purchases.append(PurchaseRecord(**item))

            logger.info(f"Loaded {len(self._purchases)} purchase records")

        except Exception as e:
            logger.error(f"Failed to load purchases: {e}")

    def _save_purchases(self) -> None:
        """Save purchases to disk."""
        try:
            data = []
            for record in self._purchases:
                item = asdict(record)
                # Convert datetime to ISO string
                if item.get("purchase_time"):
                    item["purchase_time"] = item["purchase_time"].isoformat()
                if item.get("sold_time"):
                    item["sold_time"] = item["sold_time"].isoformat()
                data.append(item)

            with open(self.purchases_file, "w") as f:
                json.dump(data, f, indent=2)

        except Exception as e:
            logger.error(f"Failed to save purchases: {e}")

    def add_purchase(self, record: PurchaseRecord) -> None:
        """Add a purchase record."""
        self._purchases.append(record)
        self._save_purchases()
        logger.info(f"Saved purchase record: {record.item_name}")

    def get_all_purchases(self) -> list[PurchaseRecord]:
        """Get all purchase records."""
        return self._purchases.copy()

    def get_successful_purchases(self) -> list[PurchaseRecord]:
        """Get only successful purchases."""
        return [p for p in self._purchases if p.success]

    def get_failed_purchases(self) -> list[PurchaseRecord]:
        """Get only failed purchases."""
        return [p for p in self._purchases if not p.success]

    def get_purchase_by_id(self, record_id: str) -> Optional[PurchaseRecord]:
        """Get a purchase by its ID."""
        for p in self._purchases:
            if p.record_id == record_id:
                return p
        return None

    def update_purchase(self, record_id: str, **updates) -> bool:
        """Update a purchase record."""
        for i, p in enumerate(self._purchases):
            if p.record_id == record_id:
                for key, value in updates.items():
                    if hasattr(p, key):
                        setattr(p, key, value)
                self._save_purchases()
                return True
        return False

    def mark_sold(
        self, record_id: str, sold_price: int, sold_time: Optional[datetime] = None
    ) -> bool:
        """Mark a purchase as sold."""
        return self.update_purchase(
            record_id,
            sold_price=sold_price,
            sold_time=sold_time or datetime.utcnow(),
        )

    def calculate_stats(self) -> PortfolioStats:
        """Calculate portfolio statistics."""
        stats = PortfolioStats()

        successful = self.get_successful_purchases()

        stats.total_purchases = len(self._purchases)
        stats.successful_purchases = len(successful)
        stats.failed_purchases = len(self._purchases) - len(successful)

        for p in successful:
            stats.total_spent += p.purchase_price
            stats.current_value += p.current_value

            if p.sold_price is not None:
                stats.realized_pnl += p.realized_pnl or 0
                if (p.realized_pnl or 0) > 0:
                    stats.winning_trades += 1
                else:
                    stats.losing_trades += 1
            else:
                if p.unrealized_pnl > 0:
                    stats.winning_trades += 1
                else:
                    stats.losing_trades += 1

        stats.unrealized_pnl = stats.current_value - stats.total_spent

        return stats

    def get_best_snipes(self, limit: int = 5) -> list[PurchaseRecord]:
        """Get best performing snipes by P&L."""
        successful = self.get_successful_purchases()
        sorted_by_pnl = sorted(
            successful,
            key=lambda p: p.realized_pnl if p.realized_pnl is not None else p.unrealized_pnl,
            reverse=True,
        )
        return sorted_by_pnl[:limit]

    def get_worst_snipes(self, limit: int = 5) -> list[PurchaseRecord]:
        """Get worst performing snipes by P&L."""
        successful = self.get_successful_purchases()
        sorted_by_pnl = sorted(
            successful,
            key=lambda p: p.realized_pnl if p.realized_pnl is not None else p.unrealized_pnl,
        )
        return sorted_by_pnl[:limit]

    def get_stats_by_strategy(self) -> dict[str, PortfolioStats]:
        """Calculate stats grouped by strategy."""
        by_strategy: dict[str, list[PurchaseRecord]] = {}

        for p in self.get_successful_purchases():
            strategy = p.strategy_used or "unknown"
            if strategy not in by_strategy:
                by_strategy[strategy] = []
            by_strategy[strategy].append(p)

        result = {}
        for strategy, purchases in by_strategy.items():
            stats = PortfolioStats()
            stats.total_purchases = len(purchases)
            stats.successful_purchases = len(purchases)

            for p in purchases:
                stats.total_spent += p.purchase_price
                stats.current_value += p.current_value

                if p.sold_price is not None:
                    stats.realized_pnl += p.realized_pnl or 0

            stats.unrealized_pnl = stats.current_value - stats.total_spent
            result[strategy] = stats

        return result

    def clear_all(self) -> None:
        """Clear all purchase records (use with caution!)."""
        self._purchases = []
        self._save_purchases()
        logger.warning("All purchase records cleared")
