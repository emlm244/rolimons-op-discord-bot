from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path

from .config import settings


@dataclass
class Alert:
    guild_id: int
    user_id: int
    item_id: int
    item_name: str
    min_op: int


class AlertStore:
    def __init__(self, path: Path | None = None) -> None:
        self.path = path or settings.data_dir / "alerts.json"
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._alerts: list[Alert] = []
        self._load()

    def _load(self) -> None:
        if not self.path.exists():
            self._alerts = []
            return
        try:
            data = json.loads(self.path.read_text())
            self._alerts = [Alert(**item) for item in data]
        except Exception:
            self._alerts = []

    def _save(self) -> None:
        payload = [asdict(alert) for alert in self._alerts]
        self.path.write_text(json.dumps(payload, indent=2))

    def add_alert(self, alert: Alert) -> None:
        self._alerts = [
            a
            for a in self._alerts
            if not (
                a.guild_id == alert.guild_id
                and a.user_id == alert.user_id
                and a.item_id == alert.item_id
            )
        ]
        self._alerts.append(alert)
        self._save()

    def list_for_guild(self, guild_id: int) -> list[Alert]:
        return [a for a in self._alerts if a.guild_id == guild_id]

    def list_all(self) -> list[Alert]:
        return list(self._alerts)
