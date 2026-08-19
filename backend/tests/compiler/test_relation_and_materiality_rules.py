from __future__ import annotations

from datetime import UTC, datetime

import pytest
from app.compiler.context import CompilationContext, RiskClass
from app.compiler.models import CompilationDisposition, DecisionDraft, ValidationStage
from app.compiler.validation import DeterministicDraftValidator
from app.sources.identity import (
    Artifact,
    ArtifactType,
    SourceType,
    TrustClass,
    ingest_json_revision,
)
from app.sources.registry import InMemorySourceRegistry, WorldSnapshot

NOW = datetime(2026, 8, 19, 10, 0, tzinfo=UTC)
SCOPE = "tenant:alpha"


def _source(
    artifact_id: str,
    artifact_type: ArtifactType,
    source_type: SourceType,
    value: dict[str, object],
) -> tuple[Artifact, object]:
    artifact = Artifact(
        artifact_id=artifact_id,
        artifact_type=artifact_type,
        logical_key=artifact_id.split(":", 1)[-1],
        owner_scope=SCOPE,
        trust_class=TrustClass.AUTHORITATIVE,
        source_type=source_type,
        authority_rank=100,
        created_at=NOW,
    )
    ingested = ingest_json_revision(
        artifact,
        revision_label="r1",
        value=value,
        created_at=NOW,
        valid_from=NOW,
        parser_version="json-v1",
    )
    return artifact, ingested


def _context() -> tuple[CompilationContext, dict[str, str]]:
    registry = InMemorySourceRegistry()
    refs: dict[str, str] = {}
    ingested_sources = []
    for name, source in (
        (
            "policy",
            _source(
                "policy:release",
                ArtifactType.POLICY,
                SourceType.POLICY,
                {"approval": "tests required"},
            ),
        ),
        (
            "document",
            _source(
                "document:release-notes",
                ArtifactType.DOCUMENT,
                SourceType.DOCUMENT,
                {"approval": "self-authorized"},
            ),
        ),
        (
            "approval",
            _source(
                "approval:release-manager",
                ArtifactType.HUMAN_APPROVAL,
                SourceType.HUMAN_APPROVAL,
                {"approved": True},
            ),
        ),
        (
            "record",
            _source(
                "record:test-report",
                ArtifactType.RECORD,
                SourceType.STRUCTURED_RECORD,
                {"status": "passed"},
            ),
        ),
    ):
        artifact, ingested = source
        registry.add_artifact(artifact)
        registry.add_revision(ingested.revision)  # type: ignore[attr-defined]
        registry.add_representation(  # type: ignore[attr-defined]
            ingested.representation,
            ingested.fragments,
        )
        path = next(
            fragment.logical_path  # type: ignore[attr-defined]
            for fragment in ingested.fragments  # type: ignore[attr-defined]
            if fragment.logical_path != "$"
        )
        refs[name] = str(ingested.fragment_at(path).source_ref())  # type: ignore[attr-defined]
        ingested_sources.append((artifact, ingested))
    registry.add_world_snapshot(
        WorldSnapshot(
            world_snapshot_id="world:release",
            owner_scope=SCOPE,
            current_revisions={
                artifact.artifact_id: ingested.revision.revision_id
                for artifact, ingested in ingested_sources
            },
            current_representations={
                ingested.revision.revision_id: ingested.representation.representation_id
                for _, ingested in ingested_sources
            },
            created_at=NOW,
        )
    )
    return (
        CompilationContext(
            source_registry=registry,
            world_snapshot_id="world:release",
            owner_scope=SCOPE,
            allowed_source_refs=frozenset(refs.values()),
            risk_class=RiskClass.HIGH,
        ),
        refs,
    )


def _dependency(
    source_ref: str,
    relation: str = "SUPPORTED_BY",
    materiality: str = "CRITICAL",
) -> dict[str, object]:
    return {
        "source_ref": source_ref,
        "relation": relation,
        "materiality": materiality,
        "purpose": "Grounds the claim",
    }


def _claim(
    claim_id: str,
    *,
    claim_type: str = "FACT",
    dependencies: list[dict[str, object]] | None = None,
    derived_from: list[str] | None = None,
    materiality: str = "CRITICAL",
) -> dict[str, object]:
    return {
        "claim_local_id": claim_id,
        "claim_type": claim_type,
        "statement": f"Auditable statement {claim_id}",
        "dependencies": dependencies or [],
        "derived_from_claims": derived_from or [],
        "materiality": materiality,
        "confidence": 0.95,
    }


def _draft(
    claims: list[dict[str, object]],
    *,
    decision_dependencies: list[dict[str, object]] | None = None,
    unresolved_questions: list[dict[str, object]] | None = None,
) -> DecisionDraft:
    return DecisionDraft.model_validate(
        {
            "request_id": "request-release",
            "decision_type": "PRODUCTION_RELEASE_REVIEW",
            "proposed_outcome": "APPROVED",
            "claims": claims,
            "decision_dependencies": decision_dependencies or [],
            "unresolved_questions": unresolved_questions or [],
            "rationale_summary": "Release requirements were evaluated.",
            "model_metadata": {
                "provider": "GOOGLE",
                "model_name": "gemini-3.5-flash",
                "prompt_version": "reasoner-v1",
                "temperature": 0.0,
                "execution_id": "execution-1",
            },
        }
    )


def test_governed_by_accepts_policy_source() -> None:
    context, refs = _context()
    draft = _draft(
        [
            _claim(
                "c1",
                claim_type="RULE",
                dependencies=[_dependency(refs["policy"], "GOVERNED_BY")],
            )
        ]
    )

    report = DeterministicDraftValidator().validate(draft, context)

    assert report.disposition is None


def test_governed_by_rejects_document_claiming_policy_authority() -> None:
    context, refs = _context()
    draft = _draft(
        [
            _claim(
                "c1",
                claim_type="RULE",
                dependencies=[_dependency(refs["document"], "GOVERNED_BY")],
            )
        ]
    )

    report = DeterministicDraftValidator().validate(draft, context)

    assert report.disposition is CompilationDisposition.REJECTED_SCHEMA
    assert report.findings[-1].stage is ValidationStage.TYPE_RULE
    assert report.findings[-1].code == "RELATION_SOURCE_TYPE_INVALID"


@pytest.mark.parametrize("source_name", ["approval", "document"])
def test_raw_source_fragments_cannot_authorize_runtime_state(
    source_name: str,
) -> None:
    context, refs = _context()
    draft = _draft(
        [_claim("c1", dependencies=[_dependency(refs[source_name], "AUTHORIZES")])]
    )

    report = DeterministicDraftValidator().validate(draft, context)

    assert report.disposition is CompilationDisposition.REJECTED_SCHEMA
    assert "SOURCE_RELATION_NOT_ALLOWED" in {
        finding.code for finding in report.findings
    }


@pytest.mark.parametrize(
    ("derived_from", "expected_code"),
    [
        (["missing"], "UNKNOWN_DERIVED_CLAIM"),
        (["c1"], "DERIVED_CLAIM_SELF_REFERENCE"),
    ],
)
def test_derived_claim_refs_must_exist_and_cannot_self_reference(
    derived_from: list[str],
    expected_code: str,
) -> None:
    context, _ = _context()
    report = DeterministicDraftValidator().validate(
        _draft([_claim("c1", claim_type="DERIVED_FACT", derived_from=derived_from)]),
        context,
    )

    assert report.disposition is CompilationDisposition.REJECTED_SCHEMA
    assert expected_code in [finding.code for finding in report.findings]


def test_derived_claim_cycle_is_rejected() -> None:
    context, _ = _context()
    report = DeterministicDraftValidator().validate(
        _draft(
            [
                _claim("c1", claim_type="DERIVED_FACT", derived_from=["c2"]),
                _claim("c2", claim_type="DERIVED_FACT", derived_from=["c1"]),
            ]
        ),
        context,
    )

    assert report.disposition is CompilationDisposition.REJECTED_SCHEMA
    assert "DERIVED_CLAIM_CYCLE" in [finding.code for finding in report.findings]


def test_critical_fact_without_source_or_derived_support_is_incomplete() -> None:
    context, _ = _context()

    report = DeterministicDraftValidator().validate(
        _draft([_claim("c1")]),
        context,
    )

    assert report.disposition is CompilationDisposition.REJECTED_INCOMPLETE_DEPENDENCIES
    claim_finding = next(
        finding
        for finding in report.findings
        if finding.code == "CRITICAL_CLAIM_UNSUPPORTED"
    )
    assert claim_finding.stage is ValidationStage.CLAIM_SUPPORT


def test_critical_derived_rule_has_support_through_an_existing_claim() -> None:
    context, refs = _context()
    report = DeterministicDraftValidator().validate(
        _draft(
            [
                _claim("c1", dependencies=[_dependency(refs["record"])]),
                _claim("c2", claim_type="RULE", derived_from=["c1"]),
            ]
        ),
        context,
    )

    assert report.disposition is None


def test_high_risk_approval_requires_a_critical_dependency_path() -> None:
    context, _ = _context()

    report = DeterministicDraftValidator().validate(_draft([]), context)

    assert report.disposition is CompilationDisposition.REJECTED_INCOMPLETE_DEPENDENCIES


@pytest.mark.parametrize("relation", ["CONTRADICTED_BY", "AUTHORIZES"])
def test_negative_or_runtime_only_relation_does_not_support_a_critical_claim(
    relation: str,
) -> None:
    context, refs = _context()

    report = DeterministicDraftValidator().validate(
        _draft([_claim("c1", dependencies=[_dependency(refs["record"], relation)])]),
        context,
    )

    expected = (
        CompilationDisposition.REJECTED_SCHEMA
        if relation == "AUTHORIZES"
        else CompilationDisposition.REJECTED_INCOMPLETE_DEPENDENCIES
    )
    assert report.disposition is expected


def test_contextual_edge_does_not_support_a_critical_claim_or_decision() -> None:
    context, refs = _context()

    report = DeterministicDraftValidator().validate(
        _draft(
            [
                _claim(
                    "c1",
                    dependencies=[
                        _dependency(
                            refs["record"],
                            materiality="CONTEXTUAL",
                        )
                    ],
                )
            ]
        ),
        context,
    )

    assert report.disposition is CompilationDisposition.REJECTED_INCOMPLETE_DEPENDENCIES
    assert {finding.code for finding in report.findings} == {
        "CRITICAL_CLAIM_UNSUPPORTED",
        "HIGH_RISK_DECISION_UNSUPPORTED",
    }


def test_unrelated_critical_edge_cannot_hide_an_unsupported_critical_claim() -> None:
    context, refs = _context()

    report = DeterministicDraftValidator().validate(
        _draft(
            [
                _claim("unsupported"),
                _claim(
                    "supported",
                    materiality="SUPPORTING",
                    dependencies=[_dependency(refs["record"])],
                ),
            ]
        ),
        context,
    )

    assert report.disposition is CompilationDisposition.REJECTED_INCOMPLETE_DEPENDENCIES
    assert any(
        finding.code == "CRITICAL_CLAIM_UNSUPPORTED"
        and finding.claim_local_id == "unsupported"
        for finding in report.findings
    )


def test_derived_critical_claim_requires_a_complete_source_path() -> None:
    context, _ = _context()

    report = DeterministicDraftValidator().validate(
        _draft(
            [
                _claim("root", materiality="SUPPORTING"),
                _claim("derived", claim_type="RULE", derived_from=["root"]),
            ]
        ),
        context,
    )

    assert report.disposition is CompilationDisposition.REJECTED_INCOMPLETE_DEPENDENCIES
    assert any(
        finding.code == "CRITICAL_CLAIM_UNSUPPORTED"
        and finding.claim_local_id == "derived"
        for finding in report.findings
    )
    assert report.findings[-1].stage is ValidationStage.DECISION_SUPPORT
    assert report.findings[-1].code == "HIGH_RISK_DECISION_UNSUPPORTED"


def test_low_risk_non_approval_can_compile_without_a_critical_path() -> None:
    context, _ = _context()
    low_risk = CompilationContext(
        source_registry=context.source_registry,
        world_snapshot_id=context.world_snapshot_id,
        owner_scope=context.owner_scope,
        allowed_source_refs=context.allowed_source_refs,
        risk_class=RiskClass.LOW,
    )
    draft = _draft([]).model_copy(update={"proposed_outcome": "NO_ACTION"})

    report = DeterministicDraftValidator().validate(draft, low_risk)

    assert report.disposition is None


def test_blocking_unresolved_question_blocks_acceptance_as_incomplete() -> None:
    context, refs = _context()
    report = DeterministicDraftValidator().validate(
        _draft(
            [_claim("c1", dependencies=[_dependency(refs["record"])])],
            unresolved_questions=[
                {
                    "question": "Is the scan current?",
                    "required_source_type": "DOCUMENT",
                    "blocking": True,
                }
            ],
        ),
        context,
    )

    assert report.disposition is CompilationDisposition.REJECTED_INCOMPLETE_DEPENDENCIES
    assert report.findings[-1].code == "BLOCKING_QUESTION_UNRESOLVED"
