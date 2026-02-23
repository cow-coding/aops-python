import time
from typing import Any


class TTLCache:
    """Simple in-memory cache with TTL expiration."""

    def __init__(self, ttl: int = 300) -> None:
        self._ttl = ttl
        self._store: dict[str, tuple[Any, float]] = {}

    def get(self, key: str) -> Any | None:
        if self._ttl == 0:
            return None
        entry = self._store.get(key)
        if entry is None:
            return None
        value, ts = entry
        if time.monotonic() - ts > self._ttl:
            del self._store[key]
            return None
        return value

    def set(self, key: str, value: Any) -> None:
        if self._ttl == 0:
            return
        self._store[key] = (value, time.monotonic())

    def invalidate(self, key: str) -> None:
        self._store.pop(key, None)

    def clear(self) -> None:
        self._store.clear()
