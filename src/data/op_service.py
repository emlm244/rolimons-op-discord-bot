"""Business logic for OP computations."""
from __future__ import annotations

import datetime as dt
import statistics
from typing import List, Optional, Sequence, Tuple

from src.data.rolimons_client import OpEntry, RolimonsClient


class OpService:
    def __init__(self, client: RolimonsClient) -> None:
        self.client = client

    async def get_typical_range(self, item_id: int, days: int = 30) -> Tuple[int, int]:
        """Return (lower, upper) typical OP values for the window."""
        entries = await self.client.fetch_op_history(item_id, months=6)
        now = dt.datetime.now(dt.timezone.utc)
        cutoff = now - dt.timedelta(days=days)
        filtered = [e for e in entries if dt.datetime.fromtimestamp(e.timestamp, dt.timezone.utc) >= cutoff]
        ops = [e.op_value for e in filtered]
        if len(ops) == 0:
            return 0, 0
        if len(ops) == 1:
            return ops[0], ops[0]
        sorted_ops = sorted(ops)
        lower_idx = max(int(len(sorted_ops) * 0.25) - 1, 0)
        upper_idx = min(int(len(sorted_ops) * 0.75), len(sorted_ops) - 1)
        return sorted_ops[lower_idx], sorted_ops[upper_idx]

    async def get_recent_proofs(self, item_id: int, months: int = 6, limit: int = 5) -> List[str]:
        entries = await self.client.fetch_op_history(item_id, months=months)
        sorted_entries = sorted(entries, key=lambda e: e.timestamp, reverse=True)
        proofs: List[str] = []
        for entry in sorted_entries:
            if entry.proof_url:
                proofs.append(entry.proof_url)
            if len(proofs) >= limit:
                break
        return proofs

    @staticmethod
    def summarize_ops(entries: Sequence[OpEntry]) -> Optional[float]:
        if not entries:
            return None
        ops = [e.op_value for e in entries]
        return statistics.mean(ops)
