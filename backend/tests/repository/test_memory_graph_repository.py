import pytest

from app.domain.models import GraphSnapshot
from app.repository.memory import InMemoryGraphRepository


def test_memory_graph_repository_rejects_duplicate_and_unknown_missions() -> None:
    repository = InMemoryGraphRepository()
    repository.create_snapshot(GraphSnapshot(mission_id="m-1"))

    with pytest.raises(ValueError, match="mission already exists"):
        repository.create_snapshot(GraphSnapshot(mission_id="m-1"))
    with pytest.raises(KeyError, match="unknown mission"):
        repository.save_snapshot(GraphSnapshot(mission_id="missing"))
    with pytest.raises(KeyError, match="unknown mission"):
        repository.has_processed_event("missing", "evt-1")


def test_memory_graph_repository_legacy_mark_methods_record_ids() -> None:
    repository = InMemoryGraphRepository()
    repository.create_snapshot(GraphSnapshot(mission_id="m-1"))

    repository.mark_event_processed("m-1", "evt-1")
    repository.mark_request_processed("m-1", "request-1")

    assert repository.has_processed_event("m-1", "evt-1")
    assert repository.has_processed_request("m-1", "request-1")
