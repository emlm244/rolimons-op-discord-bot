import asyncio
from datetime import datetime, timedelta

import pytest

from bot.data import Proof, calculate_op_ranges, calculate_typical_op
from bot.rate_limiter import SlidingWindowRateLimiter
from bot.storage import Alert, AlertStore


def test_calculate_typical_op_and_ranges():
    now = datetime.utcnow()
    proofs = [
        Proof(op=1000, date=now - timedelta(days=5), description="a"),
        Proof(op=1400, date=now - timedelta(days=10), description="b"),
        Proof(op=1200, date=now - timedelta(days=35), description="c"),
    ]
    typical = calculate_typical_op(proofs, months=1)
    assert typical == pytest.approx((1000 + 1400) / 2)
    ranges = calculate_op_ranges(typical)
    assert ranges["fair"].startswith("1,080")


def test_rate_limiter_allows_within_window():
    limiter = SlidingWindowRateLimiter(max_calls=2, window_seconds=1)
    assert limiter.allow(1)
    assert limiter.allow(1)
    assert not limiter.allow(1)
    # after sleep another call allowed
    asyncio.run(asyncio.sleep(1.1))
    assert limiter.allow(1)


def test_alert_store_round_trip(tmp_path):
    store = AlertStore(path=tmp_path / "alerts.json")
    alert = Alert(guild_id=1, user_id=2, item_id=3, item_name="Test", min_op=500)
    store.add_alert(alert)
    loaded = AlertStore(path=tmp_path / "alerts.json")
    entries = loaded.list_for_guild(1)
    assert len(entries) == 1
    assert entries[0].item_name == "Test"
