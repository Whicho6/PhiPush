from __future__ import annotations

import secrets
import threading
import time
from dataclasses import dataclass

from app.models.schemas import PlayerData


@dataclass(slots=True)
class Session:
    player: PlayerData
    expires_at: float


class MemorySessions:
    """Short-lived app sessions; Phigros credentials are never retained."""
    def __init__(self, ttl: int = 900):
        self.ttl = ttl
        self._items: dict[str, Session] = {}
        self._lock = threading.Lock()

    def create(self, player: PlayerData) -> str:
        key = secrets.token_urlsafe(32)
        with self._lock:
            self._purge()
            self._items[key] = Session(player, time.time() + self.ttl)
        return key

    def get(self, key: str | None) -> PlayerData | None:
        if not key:
            return None
        with self._lock:
            self._purge()
            item = self._items.get(key)
            return item.player if item else None

    def _purge(self) -> None:
        now = time.time()
        for key in [k for k, v in self._items.items() if v.expires_at <= now]:
            del self._items[key]
