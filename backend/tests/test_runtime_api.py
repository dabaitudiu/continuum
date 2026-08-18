from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from app.repository.runtime_memory import InMemoryRuntimeRepository


@pytest.fixture
def client() -> Iterator[TestClient]:
    with TestClient(
        create_app(runtime_repository=InMemoryRuntimeRepository())
    ) as test_client:
        yield test_client


def create_mission(client: TestClient, request_id: str = "create-1") -> str:
    response = client.post(
        "/api/missions/demo",
        json={"request_id": request_id},
    )
    assert response.status_code == 200
    return response.json()["mission_id"]


def start_mission(client: TestClient, mission_id: str, request_id: str = "start-1"):
    return client.post(
        f"/api/missions/{mission_id}/start",
        json={"request_id": request_id},
    )


def pen_test_event(mission_id: str, event_id: str = "evt-pen-1") -> dict:
    return {
        "event_id": event_id,
        "event_type": "vendor.document.uploaded",
        "mission_id": mission_id,
        "producer": "enterprise-simulator",
        "correlation_id": event_id,
        "payload": {
            "vendor_id": "ACME",
            "document_id": "document:pen-test-2026",
            "document_type": "PEN_TEST",
        },
    }


def activation_event(mission_id: str, event_id: str = "evt-window-1") -> dict:
    return {
        "event_id": event_id,
        "event_type": "procurement.activation.window.opened",
        "mission_id": mission_id,
        "producer": "enterprise-simulator",
        "correlation_id": event_id,
        "payload": {"vendor_id": "ACME"},
    }


def test_create_start_read_and_wake_runtime_mission(client: TestClient) -> None:
    mission_id = create_mission(client)

    waiting = start_mission(client, mission_id)
    summary = client.get(f"/api/missions/{mission_id}")
    commitments = client.get(f"/api/missions/{mission_id}/commitments")
    woke = client.post("/api/events", json=activation_event(mission_id))
    timeline = client.get(f"/api/missions/{mission_id}/timeline")

    assert waiting.status_code == 200
    assert waiting.json()["status"] == "WAITING"
    assert summary.status_code == 200
    assert summary.json()["status"] == "WAITING"
    assert summary.json()["counts"] == {
        "work_items": 4,
        "open_commitments": 1,
        "side_effects": 0,
    }
    assert commitments.status_code == 200
    assert commitments.json()[0]["status"] == "OPEN"
    assert woke.status_code == 200
    assert woke.json()["status"] == "RUNNING"
    assert woke.json()["result"] == {
        "matched_commitment_ids": [f"{mission_id}:commitment:activation-window"]
    }
    sequences = [event["event_sequence"] for event in timeline.json()]
    assert sequences == list(range(1, len(sequences) + 1))


def test_list_recent_missions_returns_resumable_summaries(
    client: TestClient,
) -> None:
    first = create_mission(client, "create-first")
    second = create_mission(client, "create-second")
    assert start_mission(client, first, "start-first").status_code == 200

    response = client.get("/api/missions", params={"limit": 1})

    assert response.status_code == 200
    assert response.json() == [
        {
            "mission_id": first,
            "mission_type": "VENDOR_ONBOARDING",
            "subject_id": "ACME",
            "status": "WAITING",
            "revision": 1,
            "event_sequence": 3,
            "created_at": response.json()[0]["created_at"],
            "updated_at": response.json()[0]["updated_at"],
            "counts": {
                "work_items": 4,
                "open_commitments": 1,
                "side_effects": 0,
            },
        }
    ]
    assert second != first


def test_list_recent_missions_validates_limit(client: TestClient) -> None:
    response = client.get("/api/missions", params={"limit": 0})

    assert response.status_code == 422


def test_duplicate_create_and_start_return_success_with_duplicate_flag(
    client: TestClient,
) -> None:
    first_create = client.post(
        "/api/missions/demo",
        json={"request_id": "create-1"},
    )
    second_create = client.post(
        "/api/missions/demo",
        json={"request_id": "create-1"},
    )
    mission_id = first_create.json()["mission_id"]
    first_start = start_mission(client, mission_id)
    second_start = start_mission(client, mission_id)

    assert first_create.status_code == 200
    assert second_create.status_code == 200
    assert first_create.json()["duplicate"] is False
    assert second_create.json()["duplicate"] is True
    assert first_start.json()["duplicate"] is False
    assert second_start.json()["duplicate"] is True


@pytest.mark.parametrize(
    "path",
    [
        "/api/missions/missing",
        "/api/missions/missing/timeline",
        "/api/missions/missing/commitments",
    ],
)
def test_unknown_runtime_read_has_stable_404(
    client: TestClient,
    path: str,
) -> None:
    response = client.get(path)

    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "MISSION_NOT_FOUND"


def test_unknown_runtime_start_has_stable_404(client: TestClient) -> None:
    response = start_mission(client, "missing")

    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "MISSION_NOT_FOUND"


def test_second_distinct_start_has_stable_transition_conflict(
    client: TestClient,
) -> None:
    mission_id = create_mission(client)
    assert start_mission(client, mission_id, "start-1").status_code == 200

    response = start_mission(client, mission_id, "start-2")

    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "INVALID_MISSION_TRANSITION"


def test_invalid_event_schema_has_stable_422(client: TestClient) -> None:
    mission_id = create_mission(client)
    payload = pen_test_event(mission_id)
    del payload["payload"]["document_type"]

    response = client.post("/api/events", json=payload)

    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "EVENT_SCHEMA_INVALID"


def test_missing_event_envelope_field_has_stable_422(client: TestClient) -> None:
    mission_id = create_mission(client)
    payload = pen_test_event(mission_id)
    del payload["event_id"]

    response = client.post("/api/events", json=payload)

    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "EVENT_SCHEMA_INVALID"


def test_event_for_unknown_mission_has_stable_404(client: TestClient) -> None:
    response = client.post("/api/events", json=pen_test_event("missing"))

    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "MISSION_NOT_FOUND"
