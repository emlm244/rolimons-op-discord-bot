from __future__ import annotations

import asyncio
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime, timedelta

import httpx

from .config import settings


@dataclass
class Item:
    item_id: int
    name: str
    value: int | None
    rap: int | None
    demand: str | None
    thumbnail_url: str | None


@dataclass
class Proof:
    op: int
    date: datetime
    description: str


class RolimonsClient:
    def __init__(self, items_url: str | None = None, proofs_url: str | None = None) -> None:
        self.items_url = items_url or str(settings.rolimons_items_url)
        self.proofs_url = proofs_url or str(settings.rolimons_proofs_url)
        self._client = httpx.AsyncClient(timeout=15)
        self._items_cache: dict[int, Item] = {}
        self._items_lock = asyncio.Lock()

    async def fetch_items(self) -> dict[int, Item]:
        async with self._items_lock:
            if self._items_cache:
                return self._items_cache
            response = await self._client.get(self.items_url)
            response.raise_for_status()
            payload = response.json()
            items_raw: dict[str, Iterable] = payload.get("items", {})
            items: dict[int, Item] = {}
            for key, values in items_raw.items():
                try:
                    item_id = int(key)
                    name = values[0]
                    value = values[3] if len(values) > 3 else None
                    rap = values[2] if len(values) > 2 else None
                    demand = values[6] if len(values) > 6 else None
                    thumb_hash = values[1] if len(values) > 1 else None
                    thumbnail_url = (
                        f"https://tr.rbxcdn.com/{thumb_hash}/150/150/Image.png"
                        if thumb_hash
                        else None
                    )
                    items[item_id] = Item(
                        item_id=item_id,
                        name=name,
                        value=value,
                        rap=rap,
                        demand=str(demand) if demand is not None else None,
                        thumbnail_url=thumbnail_url,
                    )
                except Exception:
                    continue
            self._items_cache = items
            return items

    async def search_item(self, query: str) -> Item | None:
        query_lower = query.lower()
        items = await self.fetch_items()
        for item in items.values():
            if item.name.lower() == query_lower:
                return item
        for item in items.values():
            if query_lower in item.name.lower():
                return item
        return None

    async def fetch_proofs(self, item_id: int, months: int = 6) -> list[Proof]:
        url = f"{self.proofs_url}/{item_id}.json"
        response = await self._client.get(url)
        if response.status_code != 200:
            return []
        payload = response.json()
        entries = payload.get("proofs", [])
        cutoff = datetime.utcnow() - timedelta(days=30 * months)
        proofs: list[Proof] = []
        for entry in entries:
            try:
                op_value = int(entry.get("op", 0))
                timestamp = entry.get("date")
                if timestamp:
                    proof_date = datetime.fromtimestamp(timestamp)
                else:
                    proof_date = datetime.utcnow()
                if proof_date < cutoff:
                    continue
                description = entry.get("note") or ""
                proofs.append(Proof(op=op_value, date=proof_date, description=description))
            except Exception:
                continue
        proofs.sort(key=lambda p: p.date, reverse=True)
        return proofs

    async def aclose(self) -> None:
        await self._client.aclose()


def calculate_typical_op(proofs: list[Proof], months: int = 1) -> float | None:
    if not proofs:
        return None
    cutoff = datetime.utcnow() - timedelta(days=30 * months)
    ops = [p.op for p in proofs if p.date >= cutoff]
    if not ops:
        return None
    return sum(ops) / len(ops)


def calculate_op_ranges(typical_op: float | None) -> dict[str, str]:
    if typical_op is None:
        return {}
    small_low = int(typical_op * 0.5)
    small_high = int(typical_op * 0.9)
    fair_low = int(typical_op * 0.9)
    fair_high = int(typical_op * 1.1)
    big_low = int(typical_op * 1.1)
    big_high = int(typical_op * 1.5)
    return {
        "small": f"{small_low:,} - {small_high:,}",
        "fair": f"{fair_low:,} - {fair_high:,}",
        "big": f"{big_low:,} - {big_high:,}",
    }
