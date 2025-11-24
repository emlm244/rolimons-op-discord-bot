import datetime as dt
import os
import sys
from pathlib import Path

import pytest

os.environ.setdefault("DISCORD_TOKEN", "test-token")
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))

from src.data.op_service import OpService
from src.data.rolimons_client import OpEntry


class DummyClient:
    def __init__(self, entries):
        self._entries = entries

    async def fetch_op_history(self, item_id: int, months: int = 6):
        return [e for e in self._entries if e.item_id == item_id]


@pytest.mark.asyncio
async def test_typical_range_empty():
    service = OpService(DummyClient([]))
    assert await service.get_typical_range(1) == (0, 0)


@pytest.mark.asyncio
async def test_typical_range_single():
    now = int(dt.datetime.now(dt.timezone.utc).timestamp())
    entry = OpEntry(item_id=1, timestamp=now, op_value=50)
    service = OpService(DummyClient([entry]))
    assert await service.get_typical_range(1) == (50, 50)


@pytest.mark.asyncio
async def test_typical_range_percentiles():
    now = int(dt.datetime.now(dt.timezone.utc).timestamp())
    entries = [
        OpEntry(item_id=1, timestamp=now, op_value=10),
        OpEntry(item_id=1, timestamp=now, op_value=20),
        OpEntry(item_id=1, timestamp=now, op_value=30),
        OpEntry(item_id=1, timestamp=now, op_value=40),
        OpEntry(item_id=1, timestamp=now, op_value=50),
    ]
    service = OpService(DummyClient(entries))
    lower, upper = await service.get_typical_range(1)
    assert lower <= upper
    assert lower == 10 or lower == 20
    assert upper == 40 or upper == 50
