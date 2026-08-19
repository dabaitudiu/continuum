from datetime import datetime
from typing import Protocol

from app.runtime.entities import InboxRecord, OutboxMessage, RuntimeSnapshot
from app.runtime.mutations import RuntimeMutation


class RuntimeRepository(Protocol):
    def create(self, snapshot: RuntimeSnapshot) -> None: ...

    def load(self, mission_id: str) -> RuntimeSnapshot: ...

    def list_recent(self, limit: int) -> list[RuntimeSnapshot]: ...

    def list_pending_outbox(
        self,
        *,
        limit: int,
        after_mission_id: str | None = None,
    ) -> list[RuntimeSnapshot]: ...

    def find_inbox(
        self,
        mission_id: str,
        message_id: str,
    ) -> InboxRecord | None: ...

    def commit(
        self,
        mission_id: str,
        expected_revision: int,
        mutation: RuntimeMutation,
    ) -> RuntimeSnapshot: ...

    def mark_outbox_published(
        self,
        mission_id: str,
        outbox_message_id: str,
        published_at: datetime,
    ) -> OutboxMessage: ...
