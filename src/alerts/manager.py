"""In-memory alert tracking with rate limiting."""
from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass
from typing import Dict, List, Optional

from discord import Interaction

from src.config import settings
from src.data.op_service import OpService

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class Alert:
    guild_id: int
    channel_id: int
    item_id: int
    min_op: int
    author_id: int
    created_at: float


class AlertManager:
    def __init__(self, service: OpService) -> None:
        self.service = service
        self.alerts: Dict[int, List[Alert]] = {}
        self.last_added: Dict[int, float] = {}
        self._task: Optional[asyncio.Task[None]] = None

    def _rate_limited(self, guild_id: int) -> bool:
        last = self.last_added.get(guild_id, 0)
        return time.time() - last < settings.alert_rate_limit_seconds

    def add_alert(self, interaction: Interaction, item_id: int, min_op: int) -> bool:
        guild_id = interaction.guild_id
        if guild_id is None:
            return False
        if self._rate_limited(guild_id):
            return False
        alert = Alert(
            guild_id=guild_id,
            channel_id=interaction.channel_id,
            item_id=item_id,
            min_op=min_op,
            author_id=interaction.user.id,
            created_at=time.time(),
        )
        self.alerts.setdefault(guild_id, []).append(alert)
        self.last_added[guild_id] = time.time()
        logger.info("Alert added for guild %s item %s >= %s", guild_id, item_id, min_op)
        return True

    async def start_polling(self, bot) -> None:  # type: ignore[override]
        if self._task:
            return
        self._task = asyncio.create_task(self._poll(bot))

    async def _poll(self, bot) -> None:  # type: ignore[override]
        await bot.wait_until_ready()
        while not bot.is_closed():
            await self._check_alerts(bot)
            await asyncio.sleep(settings.alert_poll_seconds)

    async def _check_alerts(self, bot) -> None:  # type: ignore[override]
        for guild_id, alerts in list(self.alerts.items()):
            for alert in list(alerts):
                lower, upper = await self.service.get_typical_range(alert.item_id, settings.alert_lookback_days)
                if upper >= alert.min_op:
                    channel = bot.get_channel(alert.channel_id)
                    if channel:
                        try:
                            await channel.send(
                                f"Alert: item {alert.item_id} hitting OP range {lower}-{upper} (threshold {alert.min_op})."
                            )
                        except Exception as exc:  # noqa: BLE001
                            logger.error("Failed to deliver alert for %s: %s", alert.item_id, exc)
                    alerts.remove(alert)
            if not alerts:
                self.alerts.pop(guild_id, None)
