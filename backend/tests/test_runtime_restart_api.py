from pathlib import Path

from fastapi.testclient import TestClient

from app.main import create_app
from app.repository.runtime_sqlite import SQLiteRuntimeRepository


def test_phase_g_graph_survives_runtime_repository_restart(tmp_path: Path) -> None:
    path = tmp_path / "continuum.db"
    first_repository = SQLiteRuntimeRepository(path)
    with TestClient(
        create_app(runtime_repository=first_repository)
    ) as first_client:
        mission_id = first_client.post("/api/demo/reset").json()["mission_id"]
        drift = first_client.post(
            "/api/demo/policy/upgrade",
            json={"mission_id": mission_id, "event_id": "drift-1"},
        )
        assert drift.status_code == 200
    first_repository.close()

    second_repository = SQLiteRuntimeRepository(path)
    with TestClient(
        create_app(runtime_repository=second_repository)
    ) as second_client:
        graph = second_client.get(f"/api/missions/{mission_id}/graph")
        duplicate = second_client.post(
            "/api/demo/policy/upgrade",
            json={"mission_id": mission_id, "event_id": "drift-1"},
        )

    assert graph.status_code == 200
    assert graph.json()["summary"] == {
        "stale": 2,
        "preserved": 1,
        "blocked": 1,
    }
    assert duplicate.status_code == 200
    assert duplicate.json() == graph.json()
    second_repository.close()


def test_runtime_created_mission_and_graph_route_share_one_aggregate(
    tmp_path: Path,
) -> None:
    repository = SQLiteRuntimeRepository(tmp_path / "continuum.db")
    with TestClient(create_app(runtime_repository=repository)) as client:
        created = client.post(
            "/api/missions/demo",
            json={"request_id": "create-1"},
        )
        mission_id = created.json()["mission_id"]

        summary = client.get(f"/api/missions/{mission_id}")
        graph = client.get(f"/api/missions/{mission_id}/graph")

    assert summary.status_code == 200
    assert graph.status_code == 200
    assert graph.json()["mission_id"] == mission_id
    repository.close()


def test_phase_g_reset_mission_is_visible_to_runtime_summary(
    tmp_path: Path,
) -> None:
    repository = SQLiteRuntimeRepository(tmp_path / "continuum.db")
    with TestClient(create_app(runtime_repository=repository)) as client:
        reset = client.post("/api/demo/reset")
        mission_id = reset.json()["mission_id"]

        summary = client.get(f"/api/missions/{mission_id}")

    assert summary.status_code == 200
    assert summary.json()["mission_id"] == mission_id
    assert summary.json()["event_sequence"] == 1
    repository.close()
