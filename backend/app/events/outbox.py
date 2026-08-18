from __future__ import annotations

import json
from collections.abc import Callable
from datetime import datetime
from typing import Any, Protocol

from google.cloud import pubsub_v1

from app.repository.runtime_protocol import RuntimeRepository
from app.runtime.entities import OutboxMessage, utc_now


class OutboxPublisher(Protocol):
    def publish(self, message: OutboxMessage) -> str: ...


class GooglePubSubOutboxPublisher:
    def __init__(
        self,
        client: Any,
        *,
        project: str,
        topic: str,
        publish_timeout: float = 30.0,
    ) -> None:
        self._client = client
        self._topic_path = client.topic_path(project, topic)
        self._publish_timeout = publish_timeout

    @classmethod
    def from_environment(
        cls,
        *,
        project: str,
        topic: str,
        publish_timeout: float = 30.0,
    ) -> "GooglePubSubOutboxPublisher":
        return cls(
            pubsub_v1.PublisherClient(),
            project=project,
            topic=topic,
            publish_timeout=publish_timeout,
        )

    def publish(self, message: OutboxMessage) -> str:
        envelope = {
            "event_id": message.outbox_message_id,
            "event_type": message.event_type,
            "mission_id": message.mission_id,
            "occurred_at": message.created_at.isoformat().replace("+00:00", "Z"),
            "producer": "continuum-runtime",
            "correlation_id": message.correlation_id,
            "causation_id": message.causation_id,
            "trace_id": message.trace_id,
            "payload": message.payload,
        }
        attributes = {
            "event_id": message.outbox_message_id,
            "event_type": message.event_type,
            "mission_id": message.mission_id,
            "correlation_id": message.correlation_id,
            "causation_id": message.causation_id,
        }
        if message.trace_id is not None:
            attributes["trace_id"] = message.trace_id
        future = self._client.publish(
            self._topic_path,
            json.dumps(
                envelope,
                separators=(",", ":"),
                sort_keys=True,
            ).encode("utf-8"),
            **attributes,
        )
        return str(future.result(timeout=self._publish_timeout))


class OutboxRelay:
    def __init__(
        self,
        repository: RuntimeRepository,
        publisher: OutboxPublisher,
        *,
        clock: Callable[[], datetime] = utc_now,
    ) -> None:
        self._repository = repository
        self._publisher = publisher
        self._clock = clock

    def drain(self, mission_id: str, *, limit: int = 100) -> list[str]:
        snapshot = self._repository.load(mission_id)
        pending = [
            message for message in snapshot.outbox if message.published_at is None
        ][:limit]
        published_ids: list[str] = []
        for message in pending:
            published_ids.append(self._publisher.publish(message))
            self._repository.mark_outbox_published(
                mission_id,
                message.outbox_message_id,
                self._clock(),
            )
        return published_ids
