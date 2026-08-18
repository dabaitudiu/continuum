from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any

import pytest

from app.events.outbox import GooglePubSubOutboxPublisher, OutboxRelay
from app.repository.runtime_memory import InMemoryRuntimeRepository
from app.runtime.entities import OutboxMessage
from tests.repository.runtime_contract import (
    runtime_snapshot,
    transition_mutation,
)


class FakePublishFuture:
    def __init__(self, message_id: str = "pubsub-1") -> None:
        self.message_id = message_id
        self.timeout: float | None = None

    def result(self, timeout: float | None = None) -> str:
        self.timeout = timeout
        return self.message_id


class FakePublisherClient:
    def __init__(self) -> None:
        self.calls: list[tuple[str, bytes, dict[str, str], FakePublishFuture]] = []

    def topic_path(self, project: str, topic: str) -> str:
        return f"projects/{project}/topics/{topic}"

    def publish(
        self,
        topic: str,
        data: bytes,
        **attributes: str,
    ) -> FakePublishFuture:
        future = FakePublishFuture()
        self.calls.append((topic, data, attributes, future))
        return future


def outbox_message() -> OutboxMessage:
    return OutboxMessage(
        outbox_message_id="outbox:command-1:1",
        mission_id="mission-1",
        event_type="decision.stale",
        payload={"decision_id": "D42"},
        correlation_id="correlation-1",
        causation_id="command-1",
        trace_id="trace-1",
        created_at=datetime(2026, 8, 18, 9, 0, tzinfo=UTC),
    )


def test_google_pubsub_publisher_emits_contract_envelope_and_attributes() -> None:
    client = FakePublisherClient()
    publisher = GooglePubSubOutboxPublisher(
        client,
        project="continuum-demo",
        topic="continuum-events",
    )

    published_id = publisher.publish(outbox_message())

    assert published_id == "pubsub-1"
    topic, data, attributes, future = client.calls[0]
    assert topic == "projects/continuum-demo/topics/continuum-events"
    assert json.loads(data) == {
        "event_id": "outbox:command-1:1",
        "event_type": "decision.stale",
        "mission_id": "mission-1",
        "occurred_at": "2026-08-18T09:00:00Z",
        "producer": "continuum-runtime",
        "correlation_id": "correlation-1",
        "causation_id": "command-1",
        "trace_id": "trace-1",
        "payload": {"decision_id": "D42"},
    }
    assert attributes == {
        "event_id": "outbox:command-1:1",
        "event_type": "decision.stale",
        "mission_id": "mission-1",
        "correlation_id": "correlation-1",
        "causation_id": "command-1",
        "trace_id": "trace-1",
    }
    assert future.timeout == 30.0


class RecordingPublisher:
    def __init__(self, *, fail_on: str | None = None) -> None:
        self.published: list[str] = []
        self.fail_on = fail_on

    def publish(self, message: OutboxMessage) -> str:
        if message.outbox_message_id == self.fail_on:
            raise RuntimeError("Pub/Sub unavailable")
        self.published.append(message.outbox_message_id)
        return f"pubsub:{message.outbox_message_id}"


def repository_with_outbox() -> InMemoryRuntimeRepository:
    repository = InMemoryRuntimeRepository()
    repository.create(runtime_snapshot())
    snapshot = repository.load("m-1")
    repository.commit(
        "m-1",
        snapshot.mission.revision,
        transition_mutation(snapshot, message_id="request-1"),
    )
    return repository


def test_relay_publishes_pending_messages_once_and_marks_them() -> None:
    repository = repository_with_outbox()
    publisher = RecordingPublisher()
    published_at = datetime(2026, 8, 18, 10, 0, tzinfo=UTC)
    relay = OutboxRelay(
        repository,
        publisher,
        clock=lambda: published_at,
    )

    first = relay.drain("m-1")
    second = relay.drain("m-1")

    assert first == ["pubsub:outbox:request-1"]
    assert second == []
    assert publisher.published == ["outbox:request-1"]
    assert repository.load("m-1").outbox[0].published_at == published_at


def test_relay_leaves_message_pending_when_publish_fails() -> None:
    repository = repository_with_outbox()
    publisher = RecordingPublisher(fail_on="outbox:request-1")
    relay = OutboxRelay(repository, publisher)

    with pytest.raises(RuntimeError, match="Pub/Sub unavailable"):
        relay.drain("m-1")

    assert repository.load("m-1").outbox[0].published_at is None
