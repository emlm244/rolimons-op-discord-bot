"""Lightweight Rolimon's client for OP data."""
from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import aiohttp

from src.config import settings

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class OpEntry:
    item_id: int
    timestamp: int
    op_value: int
    proof_url: Optional[str] = None


class RolimonsClient:
    def __init__(self) -> None:
        self._session: Optional[aiohttp.ClientSession] = None

    async def __aenter__(self) -> "RolimonsClient":
        await self.ensure_session()
        return self

    async def __aexit__(self, *exc_info: Any) -> None:
        await self.close()

    async def ensure_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            timeout = aiohttp.ClientTimeout(total=10)
            headers = {"User-Agent": "rolimons-op-bot/1.0"}
            if settings.rolimons_api_key:
                headers["X-API-Key"] = settings.rolimons_api_key
            self._session = aiohttp.ClientSession(timeout=timeout, headers=headers)
        return self._session

    async def close(self) -> None:
        if self._session and not self._session.closed:
            await self._session.close()

    async def fetch_op_history(self, item_id: int, months: int = 6) -> List[OpEntry]:
        """Fetch OP history entries for an item.

        The endpoint is configurable via ``ROLIMONS_BASE_URL``. The method attempts to be
        resilient to upstream errors by returning an empty list when failures occur.
        """

        session = await self.ensure_session()
        url = f"{settings.rolimons_base_url.rstrip('/')}/api/item/{item_id}/ops"
        params = {"months": months}
        try:
            async with session.get(url, params=params) as resp:
                if resp.status != 200:
                    logger.warning("Rolimons returned non-200 status %s for item %s", resp.status, item_id)
                    return []
                payload: Dict[str, Any] = await resp.json()
        except asyncio.TimeoutError:
            logger.error("Rolimons request timed out for item %s", item_id)
            return []
        except aiohttp.ClientError as exc:
            logger.error("Rolimons request failed for item %s: %s", item_id, exc)
            return []

        entries: List[OpEntry] = []
        for raw in payload.get("data", []):
            try:
                entries.append(
                    OpEntry(
                        item_id=item_id,
                        timestamp=int(raw.get("timestamp", 0)),
                        op_value=int(raw.get("op", 0)),
                        proof_url=raw.get("proof_url"),
                    )
                )
            except (TypeError, ValueError):
                logger.debug("Skipping malformed OP entry: %s", raw)
        return entries

    @staticmethod
    def item_image_url(item_id: int) -> str:
        return (
            "https://www.roblox.com/asset-thumbnail/image"
            f"?assetId={item_id}&width=420&height=420&format=png"
        )

    async def fetch_item_name(self, item_id: int) -> Optional[str]:
        """Fetch a human-readable name for the item."""
        session = await self.ensure_session()
        url = f"{settings.rolimons_base_url.rstrip('/')}/api/item/{item_id}"
        try:
            async with session.get(url) as resp:
                if resp.status != 200:
                    logger.warning("Rolimons returned non-200 for item %s: %s", item_id, resp.status)
                    return None
                payload: Dict[str, Any] = await resp.json()
        except asyncio.TimeoutError:
            logger.error("Rolimons item lookup timed out for %s", item_id)
            return None
        except aiohttp.ClientError as exc:
            logger.error("Rolimons item lookup failed for %s: %s", item_id, exc)
            return None

        return payload.get("name") or payload.get("item", {}).get("name")
