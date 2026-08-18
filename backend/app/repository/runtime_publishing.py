from __future__ import annotations

import logging
from datetime import datetime

from app.events.outbox import OutboxRelay
from app.repository.runtime_protocol import RuntimeRepository
from app.runtime.entities import InboxRecord, OutboxMessage, RuntimeSnapshot
from app.runtime.mutations import RuntimeMutation


LOGGER = logging.getLogger(__name__)


class PublishingRuntimeRepository:
    """Adds best-effort Pub/Sub dispatch without weakening domain commits.

    State is committed before publish. A transport failure leaves the durable outbox
    pending, and replay of the same command retries the relay through ``find_inbox``.
    """

    def __init__(
        self,
        repository: RuntimeRepository,
        relay: OutboxRelay,
    ) -> None:
        self._repository = repository
        self._relay = relay

    @property
    def store_kind(self) -> str:
        return str(getattr(self._repository, "store_kind", "unknown"))

    def create(self, snapshot: RuntimeSnapshot) -> None:
        self._repository.create(snapshot)
        self._drain_safely(snapshot.mission.mission_id)

    def load(self, mission_id: str) -> RuntimeSnapshot:
        return self._repository.load(mission_id)

    def list_recent(self, limit: int) -> list[RuntimeSnapshot]:
        return self._repository.list_recent(limit)

    def find_inbox(
        self,
        mission_id: str,
        message_id: str,
    ) -> InboxRecord | None:
        record = self._repository.find_inbox(mission_id, message_id)
        if record is not None:
            self._drain_safely(mission_id)
        return record

    def commit(
        self,
        mission_id: str,
        expected_revision: int,
        mutation: RuntimeMutation,
    ) -> RuntimeSnapshot:
        committed = self._repository.commit(
            mission_id,
            expected_revision,
            mutation,
        )
        if self._drain_safely(mission_id):
            return self._repository.load(mission_id)
        return committed

    def mark_outbox_published(
        self,
        mission_id: str,
        outbox_message_id: str,
        published_at: datetime,
    ) -> OutboxMessage:
        return self._repository.mark_outbox_published(
            mission_id,
            outbox_message_id,
            published_at,
        )

    def _drain_safely(self, mission_id: str) -> bool:
        try:
            self._relay.drain(mission_id)
        except Exception:
            LOGGER.exception(
                "outbox publish failed; messages remain pending",
                extra={"mission_id": mission_id},
            )
            return False
        return True
