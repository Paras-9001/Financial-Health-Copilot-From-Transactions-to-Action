from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from secrets import token_urlsafe
from threading import Lock
from uuid import UUID

from app.core import config


@dataclass
class Preview:
    user_id: UUID
    headers: list[str]
    rows: list[dict[str, str]]
    mapping: dict[str, str]
    expires_at: datetime


class PreviewStore:
    def __init__(self):
        self._items: dict[str, Preview] = {}
        self._lock = Lock()

    def put(
        self, user_id: UUID, headers: list[str], rows: list[dict[str, str]], mapping: dict[str, str]
    ) -> str:
        token = token_urlsafe(24)
        now = datetime.now(UTC)
        with self._lock:
            self._items = {k: v for k, v in self._items.items() if v.expires_at > now}
            self._items[token] = Preview(
                user_id=user_id,
                headers=headers,
                rows=rows,
                mapping=mapping,
                expires_at=now + timedelta(seconds=config.CSV_PREVIEW_TTL_SECONDS),
            )
        return token

    def get(self, token: str, user_id: UUID) -> Preview | None:
        with self._lock:
            item = self._items.get(token)
            if item is None or item.user_id != user_id or item.expires_at <= datetime.now(UTC):
                self._items.pop(token, None)
                return None
            return item

    def consume(self, token: str) -> None:
        with self._lock:
            self._items.pop(token, None)


preview_store = PreviewStore()
