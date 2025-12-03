"""Rolimons API client for fetching item data and deals."""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime
from typing import Optional

import aiohttp

from src.config import config
from src.data.models import Item, Deal, Demand, Trend

logger = logging.getLogger(__name__)


class RolimonsClient:
    """Async client for Rolimons API.

    Rate limit: 1 request per minute for itemdetails endpoint.
    Deals page can be polled more frequently.
    """

    def __init__(self, session: Optional[aiohttp.ClientSession] = None) -> None:
        """Initialize client with optional shared session."""
        self._session = session
        self._owns_session = session is None
        self._items_cache: dict[int, Item] = {}
        self._cache_time: Optional[datetime] = None
        self._cache_ttl_seconds = 60  # Cache for 1 minute (rate limit)

    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create HTTP session."""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=30),
                headers={"User-Agent": "RISniper/1.0"},
            )
            self._owns_session = True
        return self._session

    async def close(self) -> None:
        """Close the HTTP session if we own it."""
        if self._owns_session and self._session and not self._session.closed:
            await self._session.close()

    async def get_all_items(self, force_refresh: bool = False) -> dict[int, Item]:
        """Fetch all items from Rolimons itemdetails endpoint.

        This endpoint returns ALL limited items in one request.
        Rate limited to 1 request per minute.

        Returns:
            Dictionary mapping item_id to Item objects.
        """
        # Check cache
        now = datetime.utcnow()
        if (
            not force_refresh
            and self._items_cache
            and self._cache_time
            and (now - self._cache_time).total_seconds() < self._cache_ttl_seconds
        ):
            return self._items_cache

        session = await self._get_session()
        url = f"{config.rolimons_base_url}/itemapi/itemdetails"

        try:
            async with session.get(url) as response:
                if response.status != 200:
                    logger.error(f"Rolimons API error: {response.status}")
                    return self._items_cache  # Return stale cache on error

                data = await response.json()

                if not data.get("success"):
                    logger.error("Rolimons API returned success=false")
                    return self._items_cache

                items = {}
                for item_id_str, item_data in data.get("items", {}).items():
                    try:
                        item_id = int(item_id_str)
                        # item_data format: [Name, Acronym, RAP, Value, DefaultValue, Demand, Trend, Projected, Hyped, Rare]
                        items[item_id] = Item(
                            item_id=item_id,
                            name=item_data[0] if len(item_data) > 0 else "",
                            acronym=item_data[1] if len(item_data) > 1 else "",
                            rap=item_data[2] if len(item_data) > 2 and item_data[2] != -1 else 0,
                            value=item_data[3] if len(item_data) > 3 and item_data[3] != -1 else 0,
                            default_value=item_data[4] if len(item_data) > 4 and item_data[4] != -1 else 0,
                            demand=Demand(item_data[5]) if len(item_data) > 5 else Demand.NONE,
                            trend=Trend(item_data[6]) if len(item_data) > 6 else Trend.NONE,
                            projected=item_data[7] == 1 if len(item_data) > 7 else False,
                            hyped=item_data[8] == 1 if len(item_data) > 8 else False,
                            rare=item_data[9] == 1 if len(item_data) > 9 else False,
                        )
                    except (ValueError, IndexError) as e:
                        logger.warning(f"Failed to parse item {item_id_str}: {e}")
                        continue

                self._items_cache = items
                self._cache_time = now
                logger.info(f"Loaded {len(items)} items from Rolimons")
                return items

        except asyncio.TimeoutError:
            logger.error("Rolimons API request timed out")
            return self._items_cache
        except aiohttp.ClientError as e:
            logger.error(f"Rolimons API client error: {e}")
            return self._items_cache

    async def get_item(self, item_id: int, force_refresh: bool = False) -> Optional[Item]:
        """Get a single item by ID.

        Args:
            item_id: The Roblox asset ID.
            force_refresh: Force cache refresh.

        Returns:
            Item if found, None otherwise.
        """
        items = await self.get_all_items(force_refresh=force_refresh)
        return items.get(item_id)

    async def get_deals(self, min_discount: float = 20.0) -> list[Deal]:
        """Fetch current deals from Rolimons.

        Note: This scrapes the deals page. For production, consider
        using the Rolimons deals API if available, or implementing
        a proper deals fetcher.

        Args:
            min_discount: Minimum discount percentage to include.

        Returns:
            List of Deal objects sorted by discount (best first).
        """
        # Get all items first to have full data
        items = await self.get_all_items()

        # For now, we'll generate "deals" by looking at items
        # In production, this would fetch from /deals endpoint
        # or scrape the deals page

        deals = []
        # This is a placeholder - in production you'd fetch actual listings
        # from the Roblox resellers API and compare to Rolimons values

        return sorted(deals, key=lambda d: d.discount_percent, reverse=True)

    async def get_projected_items(self) -> list[int]:
        """Get list of item IDs that are marked as projected.

        These items have artificially inflated RAP and should be avoided.
        """
        items = await self.get_all_items()
        return [item_id for item_id, item in items.items() if item.projected]

    async def get_rare_items(self) -> list[int]:
        """Get list of item IDs marked as rare (<=100 copies)."""
        items = await self.get_all_items()
        return [item_id for item_id, item in items.items() if item.rare]

    async def search_items(
        self,
        query: str = "",
        min_demand: Demand = Demand.NONE,
        min_value: int = 0,
        max_value: int = 0,
        exclude_projected: bool = True,
    ) -> list[Item]:
        """Search and filter items.

        Args:
            query: Name search (case-insensitive).
            min_demand: Minimum demand level.
            min_value: Minimum value (0 = no min).
            max_value: Maximum value (0 = no max).
            exclude_projected: Exclude projected items.

        Returns:
            List of matching items.
        """
        items = await self.get_all_items()

        results = []
        query_lower = query.lower()

        for item in items.values():
            # Filter by query
            if query and query_lower not in item.name.lower():
                continue

            # Filter by demand
            if item.demand < min_demand:
                continue

            # Filter by value
            if min_value > 0 and item.value < min_value:
                continue
            if max_value > 0 and item.value > max_value:
                continue

            # Filter projected
            if exclude_projected and item.projected:
                continue

            results.append(item)

        return results
