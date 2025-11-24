import httpx
import pytest

from rolimons_bot.commands import format_op_response
from rolimons_bot.data import ItemOPRange, fetch_item_details

ITEM_ID = 123
ITEM_LOW = 150000
ITEM_HIGH = 200000
ITEM_NAME = "Dominus Astra"


@pytest.mark.asyncio
async def test_fetch_item_details_parses_payload():
    def handler(request):
        assert request.url.params["itemId"] == str(ITEM_ID)
        return httpx.Response(
            200,
            json={
                "items": {
                    str(ITEM_ID): {
                        "name": ITEM_NAME,
                        "op_low": ITEM_LOW,
                        "op_high": ITEM_HIGH,
                    }
                }
            },
        )

    transport = httpx.MockTransport(handler)

    async with httpx.AsyncClient(
        transport=transport, base_url="https://rolimons.test"
    ) as client:
        item = await fetch_item_details(
            ITEM_ID, client=client, endpoint="https://rolimons.test/items"
        )

    assert item.name == ITEM_NAME
    assert item.op_low == ITEM_LOW
    assert item.op_high == ITEM_HIGH
    assert item.as_dict()["currency"] == "R$"


def test_format_op_response_renders_range():
    item = ItemOPRange(
        item_id=ITEM_ID,
        name=ITEM_NAME,
        op_low=ITEM_LOW,
        op_high=ITEM_HIGH,
    )

    message = format_op_response(item)

    assert "Typical overpay" in message
    assert "Dominus Astra" in message
    assert "150,000–200,000" in message
