from __future__ import annotations

from pathlib import Path

from app.compiler.context import RiskClass
from app.compiler.repository import CompilationRequestRecord
from app.compiler.repository_memory import InMemoryCompilerRepository
from app.demo.compiler_fixture import (
    REFERENCE_NOW,
    REFERENCE_SCOPE,
    REFERENCE_WORLD_SNAPSHOT,
    reference_mission_id,
    reference_request_id,
)
from app.main import create_app
from app.repository.runtime_memory import InMemoryRuntimeRepository
from fastapi.testclient import TestClient
from tests.compiler.test_compiler_api import _draft, _request, _source_registry


def _demo_client(
    tmp_path: Path,
) -> tuple[
    TestClient,
    InMemoryCompilerRepository,
    InMemoryRuntimeRepository,
]:
    compiler_repository = InMemoryCompilerRepository()
    runtime_repository = InMemoryRuntimeRepository()
    app = create_app(
        runtime_repository=runtime_repository,
        compiler_repository=compiler_repository,
        compiler_budget_path=tmp_path / "openai-budget.db",
    )
    return TestClient(app), compiler_repository, runtime_repository


def test_default_compiler_fails_closed_without_a_real_or_reference_critic() -> None:
    registry, source_ref = _source_registry()
    client = TestClient(
        create_app(
            runtime_repository=InMemoryRuntimeRepository(),
            compiler_repository=InMemoryCompilerRepository(),
            compiler_source_registry=registry,
        )
    )
    client.post("/api/compiler/requests", json=_request(source_ref))
    client.post("/api/compiler/request-1/draft", json=_draft(source_ref))

    compiled = client.post("/api/compiler/request-1/compile")

    assert compiled.status_code == 200
    result = compiled.json()["result"]
    assert result["status"] == "REJECTED_INCOMPLETE_DEPENDENCIES"
    assert result["critic_findings"] == [
        {
            "finding_id": "critic:missing:0000",
            "finding_type": "MISSING_DEPENDENCY",
            "severity": "CRITICAL",
            "message": (
                "No configured completeness critic can establish that all "
                "critical dependencies were supplied."
            ),
            "candidate_ref": "UNKNOWN_SOURCE_REQUIRED",
            "claim_local_id": None,
        }
    ]


def test_reference_shaped_request_still_fails_closed_until_server_registered() -> None:
    registry, source_ref = _source_registry()
    client = TestClient(
        create_app(
            runtime_repository=InMemoryRuntimeRepository(),
            compiler_repository=InMemoryCompilerRepository(),
            compiler_source_registry=registry,
        )
    )
    forged_request_id = reference_request_id(
        "authorized-access",
        "unregistered-generic-request",
    )
    client.post(
        "/api/compiler/requests",
        json=_request(source_ref, request_id=forged_request_id),
    )
    client.post(
        f"/api/compiler/{forged_request_id}/draft",
        json=_draft(source_ref, request_id=forged_request_id),
    )

    compiled = client.post(f"/api/compiler/{forged_request_id}/compile")

    assert compiled.status_code == 200
    assert compiled.json()["result"]["status"] == ("REJECTED_INCOMPLETE_DEPENDENCIES")
    assert compiled.json()["result"]["critic_findings"][0]["candidate_ref"] == (
        "UNKNOWN_SOURCE_REQUIRED"
    )


def test_authorized_reference_scenario_compiles_and_exposes_honest_evidence(
    monkeypatch,
    tmp_path: Path,
) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    monkeypatch.delenv("GOOGLE_GENAI_USE_VERTEXAI", raising=False)
    client, _, _ = _demo_client(tmp_path)

    response = client.post(
        "/api/demo/compiler/scenarios/authorized-access",
        json={"request_id": "browser-reference-1"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["scenario_id"] == "authorized-access"
    assert payload["execution_mode"] == "DETERMINISTIC_REFERENCE"
    assert payload["aggregate"]["result"]["status"] == "ACCEPTED"
    assert payload["aggregate"]["result"]["compilation_hash"]
    assert len(payload["sources"]) == 3
    assert all(source["source_ref"] for source in payload["sources"])
    assert payload["evidence"]["deterministic_reference"]["status"] == "PASS"
    assert payload["evidence"]["openai"]["status"] == "BLOCKED"
    assert payload["evidence"]["openai"]["reason"] == (
        "OPENAI_API_KEY is not configured"
    )
    assert payload["evidence"]["openai"]["budget"] == {
        "limit_usd": "10.000000000",
        "spent_usd": "0E-9",
        "reserved_usd": "0E-9",
        "remaining_usd": "10.000000000",
        "settled_calls": 0,
        "reserved_calls": 0,
        "pricing_version": "openai-2026-08-19",
    }
    assert payload["evidence"]["gemini"]["status"] == "BLOCKED"
    assert payload["runtime_receipt"] is None


def test_reference_scenarios_cover_all_blocking_dispositions(tmp_path: Path) -> None:
    client, _, _ = _demo_client(tmp_path)
    expected = {
        "missing-governing-clause": "REJECTED_INCOMPLETE_DEPENDENCIES",
        "conflicting-authorities": "NEEDS_HUMAN_REVIEW",
        "obsolete-policy-ref": "REJECTED_STALE_SOURCE",
    }

    for scenario_id, disposition in expected.items():
        response = client.post(
            f"/api/demo/compiler/scenarios/{scenario_id}",
            json={"request_id": f"browser-{scenario_id}"},
        )
        assert response.status_code == 200
        payload = response.json()
        assert payload["aggregate"]["result"]["status"] == disposition
        assert payload["runtime_receipt"] is None


def test_demo_orchestrator_accepts_only_registered_accepted_fixture_once(
    tmp_path: Path,
) -> None:
    client, _, runtime_repository = _demo_client(tmp_path)
    compiled = client.post(
        "/api/demo/compiler/scenarios/authorized-access",
        json={"request_id": "browser-accept-1"},
    ).json()
    request_id = compiled["aggregate"]["request"]["request_id"]
    mission_id = compiled["aggregate"]["request"]["mission_id"]

    first = client.post(f"/api/demo/compiler/{request_id}/accept")
    second = client.post(f"/api/demo/compiler/{request_id}/accept")

    assert first.status_code == 200
    assert second.status_code == 200
    receipt = first.json()["runtime_receipt"]
    assert receipt["duplicate"] is False
    assert receipt["mission_revision"] == 1
    assert receipt["decision_id"]
    assert len(receipt["claim_ids"]) == 3
    assert len(receipt["evidence_ids"]) == 3
    assert receipt["audit_event_id"].startswith("audit:compiler-accept:")
    assert second.json()["runtime_receipt"]["duplicate"] is True
    assert runtime_repository.load(mission_id).mission.revision == 1

    replayed = client.post(
        "/api/demo/compiler/scenarios/authorized-access",
        json={"request_id": "browser-accept-1"},
    )
    assert replayed.status_code == 200
    assert replayed.json()["runtime_receipt"]["mission_revision"] == 1


def test_demo_orchestrator_refuses_nonaccepted_and_nonfixture_requests(
    tmp_path: Path,
) -> None:
    client, compiler_repository, runtime_repository = _demo_client(tmp_path)
    blocked = client.post(
        "/api/demo/compiler/scenarios/missing-governing-clause",
        json={"request_id": "browser-blocked-1"},
    ).json()
    blocked_request_id = blocked["aggregate"]["request"]["request_id"]
    blocked_mission_id = blocked["aggregate"]["request"]["mission_id"]
    before = runtime_repository.load(blocked_mission_id)

    rejected = client.post(f"/api/demo/compiler/{blocked_request_id}/accept")

    registry, source_ref = _source_registry()
    generic = TestClient(
        create_app(
            runtime_repository=runtime_repository,
            compiler_repository=compiler_repository,
            compiler_source_registry=registry,
        )
    )
    generic.post(
        "/api/compiler/requests",
        json=_request(source_ref, request_id="ordinary-request"),
    )
    ordinary = generic.post("/api/demo/compiler/ordinary-request/accept")

    assert rejected.status_code == 409
    assert rejected.json()["detail"]["code"] == "COMPILATION_NOT_ACCEPTED"
    assert runtime_repository.load(blocked_mission_id) == before
    assert ordinary.status_code == 403
    assert ordinary.json()["detail"]["code"] == "REFERENCE_FIXTURE_REQUIRED"


def test_reference_prefix_alone_does_not_grant_demo_runtime_capability(
    tmp_path: Path,
) -> None:
    client, compiler_repository, _ = _demo_client(tmp_path)
    forged_request_id = reference_request_id(
        "authorized-access",
        "attacker-controlled",
    )
    compiler_repository.create_request(
        CompilationRequestRecord(
            request_id=forged_request_id,
            mission_id=reference_mission_id(forged_request_id),
            work_item_id="forged-work",
            agent_id="forged-agent",
            world_snapshot_id=REFERENCE_WORLD_SNAPSHOT,
            expected_mission_revision=0,
            decision_type="PRIVILEGED_ACCESS_REVIEW",
            risk_class=RiskClass.HIGH,
            owner_scope=REFERENCE_SCOPE,
            allowed_source_refs=["forged:source@v1!representation#$.value"],
            created_at=REFERENCE_NOW,
        )
    )

    response = client.post(f"/api/demo/compiler/{forged_request_id}/accept")

    assert response.status_code == 403
    assert response.json()["detail"]["code"] == "REFERENCE_FIXTURE_REQUIRED"
