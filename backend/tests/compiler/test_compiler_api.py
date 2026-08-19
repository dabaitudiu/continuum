from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from app.compiler.canonicalization import DeterministicCanonicalizer
from app.compiler.models import CriticProposal
from app.compiler.repository_memory import InMemoryCompilerRepository
from app.compiler.review import AuthorityPrecedencePolicy, DeterministicReviewGate
from app.compiler.service import CompilerService
from app.compiler.validation import DeterministicDraftValidator
from app.main import create_app
from app.repository.runtime_memory import InMemoryRuntimeRepository
from app.sources.identity import (
    Artifact,
    ArtifactType,
    SourceType,
    TrustClass,
    ingest_json_revision,
)
from app.sources.registry import InMemorySourceRegistry, WorldSnapshot
from fastapi.testclient import TestClient

NOW = datetime(2026, 8, 19, 19, 0, tzinfo=UTC)


@dataclass
class EmptyCritic:
    def review(self, draft, context) -> CriticProposal:  # type: ignore[no-untyped-def]
        return CriticProposal()


def _compiler_service() -> CompilerService:
    return CompilerService(
        validator=DeterministicDraftValidator(),
        reviewer=DeterministicReviewGate(
            critic=EmptyCritic(),
            precedence_policy=AuthorityPrecedencePolicy(),
        ),
        canonicalizer=DeterministicCanonicalizer(
            compiler_version="sdc-1",
            validation_policy_version="validation-v1",
        ),
        compiler_version="sdc-1",
        validation_policy_version="validation-v1",
    )


def _source_registry() -> tuple[InMemorySourceRegistry, str]:
    artifact = Artifact(
        artifact_id="policy:access",
        artifact_type=ArtifactType.POLICY,
        logical_key="access-policy",
        owner_scope="tenant:alpha",
        trust_class=TrustClass.AUTHORITATIVE,
        source_type=SourceType.POLICY,
        authority_rank=100,
        created_at=NOW,
    )
    ingested = ingest_json_revision(
        artifact,
        revision_label="v13",
        value={"training": "Current training is required."},
        created_at=NOW,
        valid_from=NOW,
        parser_version="json-v1",
    )
    registry = InMemorySourceRegistry()
    registry.add_artifact(artifact)
    registry.add_revision(ingested.revision)
    registry.add_representation(
        ingested.representation,
        ingested.fragments,
        fragment_values=ingested.fragment_values,
    )
    registry.add_world_snapshot(
        WorldSnapshot(
            world_snapshot_id="world:access",
            owner_scope="tenant:alpha",
            current_revisions={artifact.artifact_id: ingested.revision.revision_id},
            current_representations={
                ingested.revision.revision_id: ingested.representation.representation_id,
            },
            created_at=NOW,
        )
    )
    return registry, str(ingested.fragment_at("$.training").source_ref())


def _draft(source_ref: str, *, request_id: str = "request-1") -> dict[str, object]:
    return {
        "request_id": request_id,
        "decision_type": "PRIVILEGED_ACCESS_REVIEW",
        "proposed_outcome": "APPROVED",
        "claims": [
            {
                "claim_local_id": "c1",
                "claim_type": "RULE",
                "statement": "Current training is required.",
                "dependencies": [
                    {
                        "source_ref": source_ref,
                        "relation": "GOVERNED_BY",
                        "materiality": "CRITICAL",
                    }
                ],
                "derived_from_claims": [],
                "materiality": "CRITICAL",
                "confidence": 0.99,
            }
        ],
        "decision_dependencies": [],
        "unresolved_questions": [],
        "rationale_summary": "The current training policy was evaluated.",
        "model_metadata": {
            "provider": "OPENAI",
            "model_name": "gpt-5.6-luna",
            "prompt_version": "reasoner-v1",
            "temperature": 0.0,
            "execution_id": "execution-1:reasoner:1",
        },
    }


def _request(source_ref: str, *, request_id: str = "request-1") -> dict[str, object]:
    return {
        "request_id": request_id,
        "mission_id": "mission-1",
        "work_item_id": "work-1",
        "agent_id": "security-agent",
        "world_snapshot_id": "world:access",
        "expected_mission_revision": 0,
        "decision_type": "PRIVILEGED_ACCESS_REVIEW",
        "risk_class": "HIGH",
        "owner_scope": "tenant:alpha",
        "allowed_source_refs": [source_ref],
    }


def _client() -> tuple[TestClient, InMemoryCompilerRepository, str]:
    registry, source_ref = _source_registry()
    repository = InMemoryCompilerRepository()
    app = create_app(
        runtime_repository=InMemoryRuntimeRepository(),
        compiler_repository=repository,
        compiler_service=_compiler_service(),
        compiler_source_registry=registry,
        runtime_compiler_capability="runtime-secret",
        compiler_api_capability="compiler-secret",
    )
    return (
        TestClient(
            app,
            headers={"X-Continuum-Compiler-Capability": "compiler-secret"},
        ),
        repository,
        source_ref,
    )


def test_five_endpoint_workflow_persists_an_auditable_compilation() -> None:
    client, repository, source_ref = _client()

    created = client.post("/api/compiler/requests", json=_request(source_ref))
    drafted = client.post(
        "/api/compiler/request-1/draft",
        json=_draft(source_ref),
    )
    compiled = client.post("/api/compiler/request-1/compile")
    loaded = client.get("/api/compiler/request-1")

    assert created.status_code == 201
    assert drafted.status_code == 200
    assert compiled.status_code == 200
    assert compiled.json()["result"]["status"] == "ACCEPTED"
    assert compiled.json()["result"]["compilation_hash"]
    assert loaded.json() == compiled.json()
    assert [event.event_type for event in repository.get("request-1").outbox] == [
        "compiler.requested",
        "compiler.draft.received",
        "compiler.accepted",
    ]


def test_compile_is_replay_safe_and_does_not_duplicate_audit_events() -> None:
    client, repository, source_ref = _client()
    client.post("/api/compiler/requests", json=_request(source_ref))
    client.post("/api/compiler/request-1/draft", json=_draft(source_ref))

    first = client.post("/api/compiler/request-1/compile")
    second = client.post("/api/compiler/request-1/compile")

    assert first.json() == second.json()
    assert len(repository.get("request-1").outbox) == 3


def test_invalid_ref_is_a_persisted_rejection_not_a_server_error() -> None:
    client, _, source_ref = _client()
    client.post("/api/compiler/requests", json=_request(source_ref))
    draft = _draft(source_ref)
    draft["claims"][0]["dependencies"][0]["source_ref"] = (  # type: ignore[index]
        "policy:invented@v1!rep-v1#section/missing"
    )
    client.post("/api/compiler/request-1/draft", json=draft)

    response = client.post("/api/compiler/request-1/compile")

    assert response.status_code == 200
    assert response.json()["result"]["status"] == "REJECTED_INVALID_REFERENCE"
    assert response.json()["result"]["compilation_hash"] is None


def test_api_maps_unknown_and_state_conflicts_to_structured_errors() -> None:
    client, _, source_ref = _client()
    missing = client.get("/api/compiler/missing")
    client.post("/api/compiler/requests", json=_request(source_ref))
    early = client.post("/api/compiler/request-1/compile")
    mismatch = client.post(
        "/api/compiler/request-1/draft",
        json=_draft(source_ref, request_id="different"),
    )

    assert missing.status_code == 404
    assert missing.json()["detail"]["code"] == "COMPILATION_REQUEST_NOT_FOUND"
    assert early.status_code == 409
    assert early.json()["detail"]["code"] == "COMPILATION_STATE_CONFLICT"
    assert mismatch.status_code == 409
    assert mismatch.json()["detail"]["code"] == "COMPILATION_DRAFT_CONFLICT"


def test_human_call_cannot_invoke_runtime_accept_capability() -> None:
    client, _, source_ref = _client()
    client.post("/api/compiler/requests", json=_request(source_ref))
    client.post("/api/compiler/request-1/draft", json=_draft(source_ref))
    client.post("/api/compiler/request-1/compile")

    response = client.post(
        "/api/compiler/request-1/accept",
        json={
            "expected_mission_revision": 0,
            "world_snapshot_id": "world:access",
        },
    )

    assert response.status_code == 403
    assert response.json()["detail"]["code"] == "RUNTIME_CAPABILITY_REQUIRED"


def test_runtime_capability_accepts_and_links_compilation_to_runtime() -> None:
    from tests.compiler.test_runtime_acceptance import _runtime_snapshot

    registry, source_ref = _source_registry()
    compiler_repository = InMemoryCompilerRepository()
    runtime_repository = InMemoryRuntimeRepository()
    runtime_repository.create(_runtime_snapshot())
    client = TestClient(
        create_app(
            runtime_repository=runtime_repository,
            compiler_repository=compiler_repository,
            compiler_service=_compiler_service(),
            compiler_source_registry=registry,
            runtime_compiler_capability="runtime-secret",
            compiler_api_capability="compiler-secret",
        ),
        headers={"X-Continuum-Compiler-Capability": "compiler-secret"},
    )
    client.post("/api/compiler/requests", json=_request(source_ref))
    client.post("/api/compiler/request-1/draft", json=_draft(source_ref))
    client.post("/api/compiler/request-1/compile")

    accepted = client.post(
        "/api/compiler/request-1/accept",
        headers={"X-Continuum-Runtime-Capability": "runtime-secret"},
        json={
            "expected_mission_revision": 0,
            "world_snapshot_id": "world:access",
        },
    )

    assert accepted.status_code == 200
    payload = accepted.json()
    assert payload["snapshot"]["mission"]["revision"] == 1
    assert (
        payload["compilation_hash"]
        == payload["snapshot"]["graph"]["decisions"][payload["decision_id"]][
            "compilation_hash"
        ]
    )


def test_public_caller_cannot_create_generic_compiler_aggregates() -> None:
    registry, source_ref = _source_registry()
    client = TestClient(
        create_app(
            runtime_repository=InMemoryRuntimeRepository(),
            compiler_repository=InMemoryCompilerRepository(),
            compiler_service=_compiler_service(),
            compiler_source_registry=registry,
        )
    )

    response = client.post("/api/compiler/requests", json=_request(source_ref))

    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "INTERNAL_COMPILER_API_DISABLED"
