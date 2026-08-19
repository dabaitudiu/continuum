from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest
from app.compiler.acceptance import CompilerAcceptanceError, RuntimeAcceptanceService
from app.compiler.context import RiskClass
from app.compiler.models import (
    CanonicalClaim,
    CanonicalEdge,
    ClaimType,
    CompilationDisposition,
    CompilationResult,
    DecisionCandidate,
    DependencyRelation,
    Materiality,
)
from app.compiler.repository import CompilationRequestRecord
from app.compiler.repository_memory import InMemoryCompilerRepository
from app.domain.invalidation import InvalidationService
from app.domain.models import DecisionStatus, DomainEvent, GraphSnapshot
from app.repository.graph_adapter import RuntimeGraphRepositoryAdapter
from app.repository.runtime_firestore import FirestoreRuntimeRepository
from app.repository.runtime_memory import InMemoryRuntimeRepository
from app.repository.runtime_sqlite import SQLiteRuntimeRepository
from app.runtime.entities import (
    EnterpriseArtifact,
    EnterpriseWorld,
    Mission,
    RuntimeSnapshot,
    VendorRecord,
)
from tests.repository.test_runtime_firestore import FakeFirestoreClient

NOW = datetime(2026, 8, 19, 20, 0, tzinfo=UTC)
SOURCE_REF = "policy:access@v13!rep-v13#section/training"


def _runtime_snapshot() -> RuntimeSnapshot:
    mission = Mission(mission_id="mission-1", revision=0)
    world = EnterpriseWorld(
        mission_id=mission.mission_id,
        vendor=VendorRecord(
            vendor_id="ACME",
            name="Acme",
            profile_revision="r1",
            handles_customer_pii=True,
        ),
        current_policy_id="policy:access",
        artifacts={
            "policy:access": EnterpriseArtifact(
                artifact_id="policy:access",
                artifact_type="POLICY",
                version="v13",
            )
        },
        world_snapshot_id="world:access",
    )
    return RuntimeSnapshot(
        mission=mission,
        world=world,
        graph=GraphSnapshot(mission_id=mission.mission_id),
    )


def _compiler_repository(
    status: CompilationDisposition = CompilationDisposition.ACCEPTED,
    *,
    request_id: str = "request-1",
    source_ref: str = SOURCE_REF,
    expected_mission_revision: int = 0,
    compilation_id: str = "compilation:one",
    decision_id: str = "decision:one",
    claim_id: str = "claim:one",
    compilation_hash: str = "a" * 64,
) -> InMemoryCompilerRepository:
    repository = InMemoryCompilerRepository()
    repository.create_request(
        CompilationRequestRecord(
            request_id=request_id,
            mission_id="mission-1",
            work_item_id="work-1",
            agent_id="security-agent",
            world_snapshot_id="world:access",
            expected_mission_revision=expected_mission_revision,
            decision_type="PRIVILEGED_ACCESS_REVIEW",
            risk_class=RiskClass.HIGH,
            owner_scope="tenant:alpha",
            allowed_source_refs=[source_ref],
            created_at=NOW,
        )
    )
    from tests.compiler.test_compiler_repository_contract import _draft

    repository.put_draft(
        request_id,
        _draft().model_copy(update={"request_id": request_id}),
    )
    accepted = status is CompilationDisposition.ACCEPTED
    repository.put_result(
        request_id,
        CompilationResult(
            compilation_id=compilation_id,
            request_id=request_id,
            status=status,
            decision_candidate=(
                DecisionCandidate(
                    decision_id=decision_id,
                    decision_type="PRIVILEGED_ACCESS_REVIEW",
                    outcome="APPROVED",
                    rationale_summary="Current policy permits access.",
                )
                if accepted
                else None
            ),
            canonical_claims=(
                [
                    CanonicalClaim(
                        claim_id=claim_id,
                        claim_local_id="c1",
                        claim_type=ClaimType.RULE,
                        statement="Current training is required.",
                        materiality=Materiality.CRITICAL,
                        confidence=0.99,
                    )
                ]
                if accepted
                else []
            ),
            canonical_edges=(
                [
                    CanonicalEdge(
                        edge_id="edge:source-claim",
                        source_kind="SOURCE_FRAGMENT",
                        source_id=source_ref,
                        target_kind="CLAIM",
                        target_id=claim_id,
                        relation=DependencyRelation.GOVERNED_BY,
                        materiality=Materiality.CRITICAL,
                    ),
                    CanonicalEdge(
                        edge_id="edge:claim-decision",
                        source_kind="CLAIM",
                        source_id=claim_id,
                        target_kind="DECISION",
                        target_id=decision_id,
                        relation=DependencyRelation.REQUIRES,
                        materiality=Materiality.CRITICAL,
                    ),
                ]
                if accepted
                else []
            ),
            compiler_version="sdc-1",
            validation_policy_version="validation-v1",
            compilation_hash=compilation_hash if accepted else None,
        ),
    )
    return repository


@pytest.fixture(params=("memory", "sqlite", "firestore"))
def runtime_repository(request, tmp_path: Path):  # type: ignore[no-untyped-def]
    if request.param == "memory":
        repository = InMemoryRuntimeRepository()
        repository.create(_runtime_snapshot())
        yield repository
    elif request.param == "sqlite":
        repository = SQLiteRuntimeRepository(tmp_path / "runtime.db")
        repository.create(_runtime_snapshot())
        yield repository
        repository.close()
    else:
        client = FakeFirestoreClient()
        repository = FirestoreRuntimeRepository(
            client,
            transaction_runner=client.run_transaction,
        )
        repository.create(_runtime_snapshot())
        yield repository


def test_accept_translates_canonical_result_and_preserves_audit_links(
    runtime_repository,
) -> None:  # type: ignore[no-untyped-def]
    service = RuntimeAcceptanceService(
        _compiler_repository(),
        runtime_repository,
    )

    accepted = service.accept(
        "request-1",
        expected_mission_revision=0,
        world_snapshot_id="world:access",
    )
    snapshot = accepted.snapshot

    assert not accepted.duplicate
    assert snapshot.mission.revision == 1
    assert snapshot.graph.decisions["decision:one"].compilation_id == "compilation:one"
    assert snapshot.graph.decisions["decision:one"].compilation_hash == "a" * 64
    assert snapshot.graph.decisions["decision:one"].world_snapshot_id == "world:access"
    assert (
        snapshot.graph.claims["claim:one"].statement == "Current training is required."
    )
    assert snapshot.graph.evidences[SOURCE_REF].artifact_id == "policy:access"
    assert {edge.edge_id for edge in snapshot.graph.edges} == {
        "edge:source-claim",
        "edge:claim-decision",
    }
    assert snapshot.audit_events[-1].payload["compilation_id"] == "compilation:one"
    assert snapshot.audit_events[-1].payload["compilation_hash"] == "a" * 64
    assert snapshot.outbox[-1].event_type == "decision.created"


def test_nonaccepted_compilation_causes_zero_runtime_mutation(
    runtime_repository,
) -> None:  # type: ignore[no-untyped-def]
    before = runtime_repository.load("mission-1")
    service = RuntimeAcceptanceService(
        _compiler_repository(CompilationDisposition.REJECTED_SCHEMA),
        runtime_repository,
    )

    with pytest.raises(CompilerAcceptanceError) as raised:
        service.accept(
            "request-1",
            expected_mission_revision=0,
            world_snapshot_id="world:access",
        )

    assert raised.value.code == "COMPILATION_NOT_ACCEPTED"
    assert runtime_repository.load("mission-1") == before


@pytest.mark.parametrize(
    ("expected_revision", "world_snapshot_id", "code"),
    [
        (1, "world:access", "MISSION_REVISION_MISMATCH"),
        (0, "world:old", "WORLD_SNAPSHOT_MISMATCH"),
    ],
)
def test_acceptance_is_bound_to_expected_revision_and_world_snapshot(
    runtime_repository,
    expected_revision: int,
    world_snapshot_id: str,
    code: str,
) -> None:  # type: ignore[no-untyped-def]
    before = runtime_repository.load("mission-1")
    service = RuntimeAcceptanceService(
        _compiler_repository(),
        runtime_repository,
    )

    with pytest.raises(CompilerAcceptanceError) as raised:
        service.accept(
            "request-1",
            expected_mission_revision=expected_revision,
            world_snapshot_id=world_snapshot_id,
        )

    assert raised.value.code == code
    assert runtime_repository.load("mission-1") == before


def test_same_compilation_acceptance_is_idempotent(runtime_repository) -> None:  # type: ignore[no-untyped-def]
    service = RuntimeAcceptanceService(
        _compiler_repository(),
        runtime_repository,
    )

    first = service.accept(
        "request-1",
        expected_mission_revision=0,
        world_snapshot_id="world:access",
    )
    second = service.accept(
        "request-1",
        expected_mission_revision=0,
        world_snapshot_id="world:access",
    )

    assert not first.duplicate
    assert second.duplicate
    assert second.snapshot.mission.revision == 1
    assert len(second.snapshot.audit_events) == 1


def test_accepted_fragment_claim_path_drives_real_runtime_invalidation() -> None:
    runtime_repository = InMemoryRuntimeRepository()
    runtime_repository.create(_runtime_snapshot())
    RuntimeAcceptanceService(
        _compiler_repository(),
        runtime_repository,
    ).accept(
        "request-1",
        expected_mission_revision=0,
        world_snapshot_id="world:access",
    )
    service = InvalidationService(RuntimeGraphRepositoryAdapter(runtime_repository))

    snapshot = service.process_artifact_change(
        "mission-1",
        DomainEvent(
            event_id="policy-v14",
            event_type="policy.version.changed",
            payload={
                "logical_key": "policy:access",
                "old_artifact_id": "policy:access",
                "new_artifact_id": "policy:access:v14",
                "old_version": "v13",
                "new_version": "v14",
            },
        ),
    )

    assert snapshot.decisions["decision:one"].status is DecisionStatus.STALE
    assert snapshot.cause_by_node_id["decision:one"] == "claim:one"


def test_recompiled_revision_is_invalidated_by_the_following_revision_change() -> None:
    runtime_repository = InMemoryRuntimeRepository()
    runtime_repository.create(_runtime_snapshot())
    RuntimeAcceptanceService(
        _compiler_repository(),
        runtime_repository,
    ).accept(
        "request-1",
        expected_mission_revision=0,
        world_snapshot_id="world:access",
    )
    invalidation = InvalidationService(
        RuntimeGraphRepositoryAdapter(runtime_repository)
    )
    invalidation.process_artifact_change(
        "mission-1",
        DomainEvent(
            event_id="policy-v14",
            event_type="policy.version.changed",
            payload={
                "logical_key": "policy:access",
                "old_artifact_id": "policy:access",
                "new_artifact_id": "policy:access:v14",
                "old_version": "v13",
                "new_version": "v14",
            },
        ),
    )

    v14_ref = SOURCE_REF.replace("@v13!", "@v14!").replace(
        "rep-v13",
        "rep-v14",
    )
    RuntimeAcceptanceService(
        _compiler_repository(
            request_id="request-2",
            source_ref=v14_ref,
            expected_mission_revision=2,
            compilation_id="compilation:two",
            decision_id="decision:two",
            claim_id="claim:two",
            compilation_hash="b" * 64,
        ),
        runtime_repository,
    ).accept(
        "request-2",
        expected_mission_revision=2,
        world_snapshot_id="world:access",
    )
    accepted = runtime_repository.load("mission-1")
    assert accepted.graph.evidences[v14_ref].artifact_id == "policy:access:v14"
    assert accepted.graph.decisions["decision:two"].status is DecisionStatus.VALID

    final = invalidation.process_artifact_change(
        "mission-1",
        DomainEvent(
            event_id="policy-v15",
            event_type="policy.version.changed",
            payload={
                "logical_key": "policy:access",
                "old_artifact_id": "policy:access:v14",
                "new_artifact_id": "policy:access:v15",
                "old_version": "v14",
                "new_version": "v15",
            },
        ),
    )

    assert final.decisions["decision:two"].status is DecisionStatus.STALE
    assert final.cause_by_node_id["decision:two"] == "claim:two"
