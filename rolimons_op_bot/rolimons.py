from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

import requests

HTTP_OK = 200


class HttpResponseProtocol(Protocol):
    status_code: int

    def json(self) -> Any:  # pragma: no cover - protocol definition
        ...


class HttpClientProtocol(Protocol):
    def get(
        self, url: str, timeout: float | None = None
    ) -> HttpResponseProtocol:  # pragma: no cover - protocol definition
        ...


@dataclass
class RolimonsItem:
    item_id: int
    name: str
    value: int
    average_op: int


class RequestsHttpClient:
    """Small adapter over ``requests`` so we can mock in tests."""

    def get(self, url: str, timeout: float | None = None) -> requests.Response:
        return requests.get(url, timeout=timeout)


class RolimonsClient:
    """Client for Rolimon's item API, designed for easy mocking in tests."""

    def __init__(
        self,
        http_client: HttpClientProtocol | None = None,
        base_url: str = "https://www.rolimons.com/api/item",
        timeout: float | None = 5.0,
    ) -> None:
        self.http_client = http_client or RequestsHttpClient()
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def fetch_item(self, item_id: int) -> RolimonsItem:
        url = f"{self.base_url}/{item_id}"
        response = self.http_client.get(url, timeout=self.timeout)
        if response.status_code != HTTP_OK:
            raise RuntimeError(f"Rolimon's request failed with status {response.status_code}")

        data = response.json()
        if not isinstance(data, dict):
            raise ValueError("Rolimon's API returned unexpected payload")

        try:
            name = str(data["name"])
            value = int(data["value"])
            average_op = int(data.get("average_op", data.get("recentAverageOP", 0)))
        except (KeyError, TypeError, ValueError) as exc:  # pragma: no cover - defensive
            raise ValueError("Rolimon's payload missing required fields") from exc

        return RolimonsItem(item_id=item_id, name=name, value=value, average_op=average_op)
