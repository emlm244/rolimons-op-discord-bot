"""Data fetching helpers for Rolimon's endpoints."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, Mapping

import httpx

DEFAULT_ITEM_ENDPOINT = os.getenv(
    "ROLIMONS_ITEM_ENDPOINT", "https://www.rolimons.com/itemapi/itemdetails"
)


@dataclass
class ItemOPRange:
    """Structured overpay range for a Rolimon's item."""

    item_id: int
    name: str
    op_low: int
    op_high: int
    currency: str = "R$"

    def as_dict(self) -> Mapping[str, Any]:
        """Return a serialisable view of the OP range."""

        return {
            "item_id": self.item_id,
            "name": self.name,
            "op_low": self.op_low,
            "op_high": self.op_high,
            "currency": self.currency,
        }


async def fetch_item_details(
    item_id: int,
    *,
    client: httpx.AsyncClient | None = None,
    endpoint: str | None = None,
    timeout: float = 10.0,
) -> ItemOPRange:
    """Fetch OP details for a single item.

    The endpoint can be overridden with ``ROLIMONS_ITEM_ENDPOINT`` or the
    ``endpoint`` argument. Reuse an ``httpx.AsyncClient`` to avoid reconnect
    overhead; otherwise a transient client is created.
    """

    item_endpoint = endpoint or DEFAULT_ITEM_ENDPOINT
    close_client = False

    if client is None:
        client = httpx.AsyncClient(timeout=timeout)
        close_client = True

    try:
        response = await client.get(item_endpoint, params={"itemId": item_id})
        response.raise_for_status()
        payload = response.json()
    finally:
        if close_client:
            await client.aclose()

    return parse_item_payload(payload, item_id)


def parse_item_payload(
    payload: Mapping[str, Any], item_id: int
) -> ItemOPRange:
    """Parse the Rolimon's item payload into a structured OP range."""

    items = payload.get("items") or {}
    str_item_id = str(item_id)
    item_key = str_item_id if str_item_id in items else item_id
    item_details = items.get(item_key)

    if not item_details:
        raise ValueError(f"Item {item_id} not found in payload")

    try:
        name = str(item_details["name"])
        op_low = int(item_details["op_low"])
        op_high = int(item_details["op_high"])
    except KeyError as exc:  # pragma: no cover - defensive clause
        raise ValueError("Payload missing required keys") from exc

    return ItemOPRange(
        item_id=item_id,
        name=name,
        op_low=op_low,
        op_high=op_high,
    )
