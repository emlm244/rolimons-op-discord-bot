from typing import Any

import pytest

from rolimons_op_bot.rolimons import RolimonsClient, RolimonsItem


class DummyResponse:
    def __init__(self, status_code: int, payload: object):
        self.status_code = status_code
        self._payload = payload

    def json(self) -> Any:  # pragma: no cover - exercised in tests
        return self._payload


class DummyHttpClient:
    def __init__(self, response: DummyResponse):
        self.response = response
        self.requested_urls: list[str] = []

    def get(self, url: str, timeout: float | None = None) -> DummyResponse:
        self.requested_urls.append(url)
        return self.response


def test_fetch_item_success() -> None:
    response = DummyResponse(
        status_code=200,
        payload={"name": "Valk", "value": 65000, "average_op": 12000},
    )
    client = RolimonsClient(
        http_client=DummyHttpClient(response), base_url="https://example.com/item"
    )

    item = client.fetch_item(123)

    assert item == RolimonsItem(item_id=123, name="Valk", value=65000, average_op=12000)


def test_fetch_item_handles_non_200() -> None:
    client = RolimonsClient(
        http_client=DummyHttpClient(DummyResponse(500, {})), base_url="https://example.com/item"
    )
    with pytest.raises(RuntimeError):
        client.fetch_item(999)


def test_fetch_item_validates_payload_shape() -> None:
    client = RolimonsClient(
        http_client=DummyHttpClient(DummyResponse(200, [])), base_url="https://example.com/item"
    )
    with pytest.raises(ValueError):
        client.fetch_item(999)
