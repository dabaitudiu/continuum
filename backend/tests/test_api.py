import inspect

from fastapi.testclient import TestClient

from app.main import create_app
from app.repository.memory import InMemoryGraphRepository


class RouteWriteGuardRepository(InMemoryGraphRepository):
    def save_snapshot(self, snapshot):  # type: ignore[no-untyped-def]
        direct_caller_module = inspect.stack()[1].frame.f_globals.get("__name__")
        assert direct_caller_module != "app.main", (
            "API routes must delegate state transitions to domain services"
        )
        super().save_snapshot(snapshot)


def test_reset_then_upgrade_returns_required_graph_without_direct_status_writes() -> None:
    repo = RouteWriteGuardRepository()
    client = TestClient(create_app(repo))

    reset = client.post("/api/demo/reset")
    assert reset.status_code == 200
    mission_id = reset.json()["mission_id"]
    drift = client.post(
        "/api/demo/policy/upgrade",
        json={"mission_id": mission_id, "event_id": "evt-api-1"},
    )

    assert drift.status_code == 200
    body = drift.json()
    assert body["summary"] == {"stale": 2, "preserved": 1, "blocked": 1}
    statuses = {node["id"]: node["status"] for node in body["nodes"]}
    assert {
        node_id: statuses[node_id]
        for node_id in ("D42", "D43", "D50", "activate-vendor")
    } == {
        "D42": "STALE",
        "D43": "VALID",
        "D50": "STALE",
        "activate-vendor": "BLOCKED",
    }


def reset_mission(client: TestClient) -> str:
    response = client.post("/api/demo/reset")
    assert response.status_code == 200
    return response.json()["mission_id"]


def upgrade_mission(
    client: TestClient,
    mission_id: str,
    event_id: str = "evt-api-upgrade",
):  # type: ignore[no-untyped-def]
    return client.post(
        "/api/demo/policy/upgrade",
        json={"mission_id": mission_id, "event_id": event_id},
    )


def test_duplicate_event_returns_identical_graph_without_replaying_transition() -> None:
    client = TestClient(create_app(InMemoryGraphRepository()))
    mission_id = reset_mission(client)

    first = upgrade_mission(client, mission_id, "evt-duplicate")
    second = upgrade_mission(client, mission_id, "evt-duplicate")

    assert second.status_code == 200
    assert second.json() == first.json()
    assert len(second.json()["events"]) == 1


def test_revalidation_dispatches_only_d42_and_duplicate_request_is_idempotent() -> None:
    client = TestClient(create_app(InMemoryGraphRepository()))
    mission_id = reset_mission(client)
    assert upgrade_mission(client, mission_id).status_code == 200

    first = client.post(
        f"/api/missions/{mission_id}/revalidate",
        json={"request_id": "request-api-1"},
    )
    second = client.post(
        f"/api/missions/{mission_id}/revalidate",
        json={"request_id": "request-api-1"},
    )

    assert first.status_code == 200
    assert second.json() == first.json()
    body = first.json()
    assert [record["decision_id"] for record in body["dispatches"]] == ["D42"]
    nodes = {node["id"]: node for node in body["nodes"]}
    assert nodes["D42"]["status"] == "REVALIDATING"
    assert nodes["D42"]["execution_count"] == 2
    assert nodes["D50"]["status"] == "STALE"
    assert nodes["D50"]["execution_count"] == 1
    assert nodes["D43"]["status"] == "VALID"
    assert nodes["D43"]["execution_count"] == 1
    assert body["plan"]["waiting_decision_ids"] == ["D50"]


def test_unknown_mission_has_stable_404_contract() -> None:
    client = TestClient(create_app(InMemoryGraphRepository()))

    response = client.get("/api/missions/missing/graph")

    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "MISSION_NOT_FOUND"


def test_unknown_mission_command_endpoints_share_404_contract() -> None:
    client = TestClient(create_app(InMemoryGraphRepository()))

    upgrade = upgrade_mission(client, "missing")
    revalidate = client.post(
        "/api/missions/missing/revalidate",
        json={"request_id": "request-missing"},
    )

    assert upgrade.status_code == 404
    assert upgrade.json()["detail"]["code"] == "MISSION_NOT_FOUND"
    assert revalidate.status_code == 404
    assert revalidate.json()["detail"]["code"] == "MISSION_NOT_FOUND"


def test_second_distinct_upgrade_has_stable_version_conflict_contract() -> None:
    client = TestClient(create_app(InMemoryGraphRepository()))
    mission_id = reset_mission(client)
    assert upgrade_mission(client, mission_id, "evt-first").status_code == 200

    response = upgrade_mission(client, mission_id, "evt-second")

    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "POLICY_VERSION_CONFLICT"


def test_revalidation_before_drift_has_stable_conflict_contract() -> None:
    client = TestClient(create_app(InMemoryGraphRepository()))
    mission_id = reset_mission(client)

    response = client.post(
        f"/api/missions/{mission_id}/revalidate",
        json={"request_id": "request-too-early"},
    )

    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "REVALIDATION_NOT_AVAILABLE"


def test_reset_graph_is_initial_before_policy_drift() -> None:
    client = TestClient(create_app(InMemoryGraphRepository()))
    mission_id = reset_mission(client)

    response = client.get(f"/api/missions/{mission_id}/graph")

    assert response.status_code == 200
    assert response.json()["phase"] == "INITIAL"
    assert response.json()["summary"] == {
        "stale": 0,
        "preserved": 3,
        "blocked": 0,
    }
