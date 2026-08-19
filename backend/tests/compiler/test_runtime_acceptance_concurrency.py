from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from app.compiler.acceptance import RuntimeAcceptanceService
from app.repository.runtime_sqlite import SQLiteRuntimeRepository
from tests.compiler.test_runtime_acceptance import (
    _compiler_repository,
    _runtime_snapshot,
)


def test_concurrent_acceptance_commits_exactly_one_runtime_mutation(
    tmp_path: Path,
) -> None:
    path = tmp_path / "runtime.db"
    first_repository = SQLiteRuntimeRepository(path)
    second_repository = SQLiteRuntimeRepository(path)
    first_repository.create(_runtime_snapshot())
    compiler_repository = _compiler_repository()
    services = (
        RuntimeAcceptanceService(compiler_repository, first_repository),
        RuntimeAcceptanceService(compiler_repository, second_repository),
    )

    def accept(service: RuntimeAcceptanceService):  # type: ignore[no-untyped-def]
        return service.accept(
            "request-1",
            expected_mission_revision=0,
            world_snapshot_id="world:access",
        )

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(accept, services))

    snapshot = first_repository.load("mission-1")
    assert sorted(result.duplicate for result in results) == [False, True]
    assert snapshot.mission.revision == 1
    assert len(snapshot.graph.decisions) == 1
    assert len(snapshot.audit_events) == 1
    first_repository.close()
    second_repository.close()
