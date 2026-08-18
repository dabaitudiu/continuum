from fastapi.testclient import TestClient

from app.main import create_app
from app.repository.runtime_memory import InMemoryRuntimeRepository


def test_control_read_model_tracks_complete_browser_story() -> None:
    with TestClient(
        create_app(runtime_repository=InMemoryRuntimeRepository())
    ) as client:
        created = client.post(
            "/api/missions/demo",
            json={"request_id": "create-control"},
        ).json()
        mission_id = created["mission_id"]

        control = client.get(f"/api/missions/{mission_id}/control").json()
        assert control["scenario_phase"] == "CREATED"
        assert control["next_action"] == "START"
        assert control["execution_mode"] == "LOCAL_DETERMINISTIC"

        client.post(
            f"/api/missions/{mission_id}/start",
            json={"request_id": "start-control"},
        )
        control = client.get(f"/api/missions/{mission_id}/control").json()
        assert control["scenario_phase"] == "BASELINE_WAITING"
        assert control["next_action"] == "INJECT_POLICY"
        assert not any(
            item["event_type"] == "vendor.document.uploaded"
            for item in control["commitments"]
        )

        client.post(
            "/api/demo/policy/upgrade",
            json={"mission_id": mission_id, "event_id": "policy-control"},
        )
        control = client.get(f"/api/missions/{mission_id}/control").json()
        assert control["scenario_phase"] == "POLICY_DRIFT"
        assert control["graph"]["plan"]["retained_decision_ids"] == ["D43"]

        client.post(
            f"/api/missions/{mission_id}/revalidate",
            json={"request_id": "revalidate-control"},
        )
        control = client.get(f"/api/missions/{mission_id}/control").json()
        assert control["scenario_phase"] == "MISSING_EVIDENCE"
        assert control["next_action"] == "UPLOAD_PEN_TEST"

        uploaded = client.post(
            "/api/demo/documents/pen-test",
            json={"mission_id": mission_id, "event_id": "pen-control"},
        )
        assert uploaded.status_code == 200
        control = client.get(f"/api/missions/{mission_id}/control").json()
        assert control["scenario_phase"] == "COMPLETED"
        assert control["vendor_status"] == "ACTIVE"
        assert control["mission"]["status"] == "COMPLETED"
        assert len(control["side_effects"]) == 1
