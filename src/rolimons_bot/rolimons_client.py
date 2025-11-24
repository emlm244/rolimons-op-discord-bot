from __future__ import annotations

import json
import re
import time
from collections.abc import Iterable
from dataclasses import dataclass

import httpx

USER_AGENT = "rolimons-op-bot/0.1 (+https://github.com/)"
BASE_ITEM_URL = "https://www.rolimons.com/item/{item_id}"


class RolimonsError(Exception):
    """Base Rolimon's error."""


class ItemNotFoundError(RolimonsError):
    """Raised when an item cannot be fetched or parsed."""


class ParsingError(RolimonsError):
    """Raised when expected data cannot be parsed from the page."""


@dataclass
class ItemDetails:
    item_id: int
    name: str
    acronym: str | None
    rap: int
    value: int | None
    demand: int | None
    trend: int | None
    projected: bool
    hyped: bool
    rare: bool
    thumbnail_url: str


@dataclass
class ItemHistory:
    timestamps: list[int]
    rap_history: list[int]
    best_price_history: list[int]

    def last_month_ops(self, now: float | None = None) -> list[int]:
        """Compute overpay estimates for the last 30 days using best price minus RAP."""
        current = int(now or time.time())
        cutoff = current - 30 * 24 * 60 * 60
        op_values: list[int] = []
        for ts, rap, best_price in zip(
            self.timestamps, self.rap_history, self.best_price_history, strict=False
        ):
            if ts >= cutoff:
                op_values.append(max(best_price - rap, 0))
        if not op_values:
            # fall back to using all data if the item is very stale
            op_values = [
                max(bp - rp, 0)
                for bp, rp in zip(self.best_price_history, self.rap_history, strict=False)
            ]
        return op_values


def _extract_json(payload: str, marker: str) -> dict:
    match = re.search(rf"{re.escape(marker)}\s*=\s*(\{{[^;]+\}});", payload)
    if not match:
        raise ParsingError(f"Could not find {marker}")
    try:
        return json.loads(match.group(1))
    except json.JSONDecodeError as exc:
        raise ParsingError(f"Failed to parse {marker}") from exc


def parse_item_page(body: str, item_id: int) -> tuple[ItemDetails, ItemHistory]:
    details_raw = _extract_json(body, "item_details_data")
    if details_raw.get("item_id") != item_id:
        raise ParsingError("Item ID mismatch in parsed data")

    history_raw = _extract_json(body, "history_data")
    timestamps = history_raw.get("timestamp")
    rap_history = history_raw.get("rap")
    best_price_history = history_raw.get("best_price")

    if not (
        isinstance(timestamps, list)
        and isinstance(rap_history, list)
        and isinstance(best_price_history, list)
    ):
        raise ParsingError("Incomplete history data")

    details = ItemDetails(
        item_id=item_id,
        name=str(details_raw.get("item_name", "Unknown Item")),
        acronym=details_raw.get("acronym") or None,
        rap=int(details_raw.get("rap", 0)),
        value=(
            int(details_raw["value"])
            if "value" in details_raw and details_raw["value"] is not None
            else None
        ),
        demand=(
            int(details_raw["demand"])
            if "demand" in details_raw and details_raw["demand"] is not None
            else None
        ),
        trend=(
            int(details_raw["trend"])
            if "trend" in details_raw and details_raw["trend"] is not None
            else None
        ),
        projected=bool(details_raw.get("projected", False)),
        hyped=bool(details_raw.get("hyped", False)),
        rare=bool(details_raw.get("rare", False)),
        thumbnail_url=str(details_raw.get("thumbnail_url_lg", "")),
    )

    history = ItemHistory(
        timestamps=[int(ts) for ts in timestamps],
        rap_history=[int(val) for val in rap_history],
        best_price_history=[int(val) for val in best_price_history],
    )
    return details, history


async def fetch_item_page(item_id: int) -> str:
    url = BASE_ITEM_URL.format(item_id=item_id)
    async with httpx.AsyncClient(timeout=15.0, headers={"User-Agent": USER_AGENT}) as client:
        response = await client.get(url)
        if response.status_code == 404:
            raise ItemNotFoundError(f"Item {item_id} not found")
        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise RolimonsError(f"Failed to fetch item page: {exc}") from exc
        return response.text


async def get_item(item_id: int) -> tuple[ItemDetails, ItemHistory]:
    page_body = await fetch_item_page(item_id)
    return parse_item_page(page_body, item_id)


def percentile_bands(values: Iterable[int]) -> tuple[int, int, int]:
    data = sorted(values)
    if not data:
        raise ValueError("No data to compute percentiles")
    def percentile(p: float) -> int:
        idx = (len(data) - 1) * p
        lower = int(idx)
        upper = min(lower + 1, len(data) - 1)
        weight = idx - lower
        return int(round(data[lower] * (1 - weight) + data[upper] * weight))

    return percentile(0.25), percentile(0.5), percentile(0.75)
