from __future__ import annotations

from app.events.outbox import OutboxRelay
from app.repository.runtime_memory import InMemoryRuntimeRepository
from app.repository.runtime_publishing import PublishingRuntimeRepository
from app.runtime.entities import OutboxMessage
from tests.events.test_outbox import RecordingPublisher
from tests.repository.runtime_contract import (
    runtime_snapshot,
    transition_mutation,
)


def test_successful_commit_is_published_and_marked_before_return() -> None:
    underlying = InMemoryRuntimeRepository()
    publisher = RecordingPublisher()
    repository = PublishingRuntimeRepository(
        underlying,
        OutboxRelay(underlying, publisher),
    )
    repository.create(runtime_snapshot())
    initial = repository.load("m-1")

    committed = repository.commit(
        "m-1",
        initial.mission.revision,
        transition_mutation(initial, message_id="request-1"),
    )

    assert publisher.published == ["outbox:request-1"]
    assert committed.outbox[0].published_at is not None


def test_publish_failure_keeps_domain_commit_and_duplicate_retry_drains_outbox() -> None:
    underlying = InMemoryRuntimeRepository()
    publisher = RecordingPublisher(fail_on="outbox:request-1")
    repository = PublishingRuntimeRepository(
        underlying,
        OutboxRelay(underlying, publisher),
    )
    repository.create(runtime_snapshot())
    initial = repository.load("m-1")

    committed = repository.commit(
        "m-1",
        initial.mission.revision,
        transition_mutation(initial, message_id="request-1"),
    )

    assert committed.mission.revision == 1
    assert committed.outbox[0].published_at is None
    publisher.fail_on = None

    duplicate = repository.find_inbox("m-1", "request-1")

    assert duplicate is not None
    assert publisher.published == ["outbox:request-1"]
    assert repository.load("m-1").outbox[0].published_at is not None


def test_initial_outbox_is_published_after_create() -> None:
    underlying = InMemoryRuntimeRepository()
    publisher = RecordingPublisher()
    repository = PublishingRuntimeRepository(
        underlying,
        OutboxRelay(underlying, publisher),
    )
    snapshot = runtime_snapshot()
    snapshot.outbox.append(
        OutboxMessage(
            outbox_message_id="outbox:create-1",
            mission_id="m-1",
            event_type="mission.created",
            correlation_id="create-1",
            causation_id="create-1",
        )
    )

    repository.create(snapshot)

    assert publisher.published == ["outbox:create-1"]


def test_list_recent_delegates_without_publishing() -> None:
    underlying = InMemoryRuntimeRepository()
    publisher = RecordingPublisher()
    repository = PublishingRuntimeRepository(
        underlying,
        OutboxRelay(underlying, publisher),
    )
    repository.create(runtime_snapshot("m-1"))
    repository.create(runtime_snapshot("m-2"))

    recent = repository.list_recent(1)

    assert [item.mission.mission_id for item in recent] == ["m-2"]
    assert publisher.published == []
