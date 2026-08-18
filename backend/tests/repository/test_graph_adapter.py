import pytest

from app.demo.fixture import seed_canonical_mission
from app.domain.models import DecisionStatus
from app.repository.graph_adapter import RuntimeGraphRepositoryAdapter
from app.repository.runtime_memory import InMemoryRuntimeRepository


def test_adapter_creates_and_reads_graph_inside_runtime_aggregate() -> None:
    runtime_repository = InMemoryRuntimeRepository()
    adapter = RuntimeGraphRepositoryAdapter(runtime_repository)

    mission_id = seed_canonical_mission(adapter, "m-1")

    aggregate = runtime_repository.load(mission_id)
    assert aggregate.graph == adapter.get_snapshot(mission_id)
    assert aggregate.mission.mission_id == mission_id
    assert aggregate.mission.event_sequence == 1
    assert aggregate.audit_events[0].event_type == "mission.created"


def test_adapter_saves_graph_and_processed_event_in_one_runtime_commit() -> None:
    runtime_repository = InMemoryRuntimeRepository()
    adapter = RuntimeGraphRepositoryAdapter(runtime_repository)
    seed_canonical_mission(adapter, "m-1")
    graph = adapter.get_snapshot("m-1")
    graph.decisions["D42"].status = DecisionStatus.STALE

    adapter.save_snapshot(graph, processed_event_id="evt-1")

    aggregate = runtime_repository.load("m-1")
    assert aggregate.graph.decisions["D42"].status is DecisionStatus.STALE
    assert adapter.has_processed_event("m-1", "evt-1")
    assert aggregate.inbox[-1].message_id == "graph:event:evt-1"
    assert aggregate.audit_events[-1].event_type == "graph.event.applied"


def test_adapter_saves_graph_and_processed_request_in_one_runtime_commit() -> None:
    runtime_repository = InMemoryRuntimeRepository()
    adapter = RuntimeGraphRepositoryAdapter(runtime_repository)
    seed_canonical_mission(adapter, "m-1")
    graph = adapter.get_snapshot("m-1")

    adapter.save_snapshot(graph, processed_request_id="request-1")

    assert adapter.has_processed_request("m-1", "request-1")
    assert runtime_repository.load("m-1").inbox[-1].message_id == (
        "graph:request:request-1"
    )


def test_adapter_maps_unknown_runtime_mission_to_graph_key_error() -> None:
    adapter = RuntimeGraphRepositoryAdapter(InMemoryRuntimeRepository())

    with pytest.raises(KeyError, match="unknown mission"):
        adapter.get_snapshot("missing")


def test_adapter_rejects_duplicate_graph_mission() -> None:
    adapter = RuntimeGraphRepositoryAdapter(InMemoryRuntimeRepository())
    seed_canonical_mission(adapter, "m-1")

    with pytest.raises(ValueError, match="mission already exists"):
        seed_canonical_mission(adapter, "m-1")


def test_adapter_rejects_save_for_unknown_mission() -> None:
    adapter = RuntimeGraphRepositoryAdapter(InMemoryRuntimeRepository())

    with pytest.raises(KeyError, match="unknown mission"):
        adapter.save_snapshot(
            seed_graph_only("missing"),
            processed_event_id="evt-1",
        )


def test_adapter_rejects_event_and_request_in_same_save() -> None:
    adapter = RuntimeGraphRepositoryAdapter(InMemoryRuntimeRepository())

    with pytest.raises(ValueError, match="either an event or a request"):
        adapter.save_snapshot(
            seed_graph_only("m-1"),
            processed_event_id="evt-1",
            processed_request_id="request-1",
        )


def test_adapter_plain_save_is_revision_idempotent() -> None:
    runtime_repository = InMemoryRuntimeRepository()
    adapter = RuntimeGraphRepositoryAdapter(runtime_repository)
    seed_canonical_mission(adapter, "m-1")
    graph = adapter.get_snapshot("m-1")

    adapter.save_snapshot(graph)
    after_first = runtime_repository.load("m-1")
    adapter.save_snapshot(graph, processed_request_id="request-1")
    adapter.save_snapshot(graph, processed_request_id="request-1")
    after_duplicate = runtime_repository.load("m-1")

    assert after_first.audit_events[-1].event_type == "graph.snapshot.saved"
    assert after_duplicate.mission.revision == after_first.mission.revision + 1


def test_legacy_mark_methods_are_idempotent() -> None:
    runtime_repository = InMemoryRuntimeRepository()
    adapter = RuntimeGraphRepositoryAdapter(runtime_repository)
    seed_canonical_mission(adapter, "m-1")

    adapter.mark_event_processed("m-1", "evt-1")
    adapter.mark_event_processed("m-1", "evt-1")
    adapter.mark_request_processed("m-1", "request-1")
    adapter.mark_request_processed("m-1", "request-1")

    aggregate = runtime_repository.load("m-1")
    assert adapter.has_processed_event("m-1", "evt-1")
    assert adapter.has_processed_request("m-1", "request-1")
    assert aggregate.mission.revision == 2


def test_adapter_processed_lookup_maps_unknown_mission_to_key_error() -> None:
    adapter = RuntimeGraphRepositoryAdapter(InMemoryRuntimeRepository())

    with pytest.raises(KeyError, match="unknown mission"):
        adapter.has_processed_event("missing", "evt-1")


def seed_graph_only(mission_id: str):  # type: ignore[no-untyped-def]
    runtime_repository = InMemoryRuntimeRepository()
    temporary = RuntimeGraphRepositoryAdapter(runtime_repository)
    seed_canonical_mission(temporary, mission_id)
    return temporary.get_snapshot(mission_id)
