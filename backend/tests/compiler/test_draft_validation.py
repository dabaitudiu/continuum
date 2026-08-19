from __future__ import annotations

from datetime import UTC, datetime

import pytest

from app.compiler.context import CompilationContext, RiskClass
from app.compiler.models import CompilationDisposition, DecisionDraft, ValidationStage
from app.compiler.validation import DeterministicDraftValidator
from app.sources.identity import (
    Artifact,
    ArtifactType,
    SourceRef,
    SourceType,
    TrustClass,
    ingest_json_revision,
)
from app.sources.registry import InMemorySourceRegistry, WorldSnapshot


NOW = datetime(2026, 8, 19, 9, 0, tzinfo=UTC)
SCOPE = "tenant:alpha"


def _artifact() -> Artifact:
    return Artifact(
        artifact_id="policy:access",
        artifact_type=ArtifactType.POLICY,
        logical_key="access-policy",
        owner_scope=SCOPE,
        trust_class=TrustClass.AUTHORITATIVE,
        source_type=SourceType.POLICY,
        authority_rank=100,
        created_at=NOW,
    )


def _registry() -> tuple[InMemorySourceRegistry, str, str, str]:
    registry = InMemorySourceRegistry()
    artifact = _artifact()
    registry.add_artifact(artifact)
    old = ingest_json_revision(
        artifact,
        revision_label="v12",
        value={"training": "optional"},
        created_at=NOW,
        valid_from=NOW,
        parser_version="json-v1",
    )
    current = ingest_json_revision(
        artifact,
        revision_label="v13",
        value={"training": "required"},
        created_at=NOW,
        valid_from=NOW,
        parser_version="json-v1",
    )
    for ingested in (old, current):
        registry.add_revision(ingested.revision)
        registry.add_representation(ingested.representation, ingested.fragments)
    registry.add_world_snapshot(
        WorldSnapshot(
            world_snapshot_id="world:access-13",
            owner_scope=SCOPE,
            current_revisions={artifact.artifact_id: current.revision.revision_id},
            current_representations={
                current.revision.revision_id: current.representation.representation_id,
            },
            created_at=NOW,
        )
    )
    return (
        registry,
        str(old.fragment_at("$.training").source_ref()),
        str(current.fragment_at("$.training").source_ref()),
        current.representation.representation_id,
    )


def _draft(source_ref: str) -> DecisionDraft:
    return DecisionDraft.model_validate(
        {
            "request_id": "request-access-1",
            "decision_type": "PRIVILEGED_ACCESS_REVIEW",
            "proposed_outcome": "APPROVED",
            "claims": [
                {
                    "claim_local_id": "c1",
                    "claim_type": "RULE",
                    "statement": "Current security training is required.",
                    "dependencies": [
                        {
                            "source_ref": source_ref,
                            "relation": "GOVERNED_BY",
                            "materiality": "CRITICAL",
                            "purpose": "Defines the approval requirement",
                        }
                    ],
                    "derived_from_claims": [],
                    "materiality": "CRITICAL",
                    "confidence": 0.99,
                }
            ],
            "decision_dependencies": [],
            "unresolved_questions": [],
            "rationale_summary": "The policy requirement applies.",
            "model_metadata": {
                "provider": "GOOGLE",
                "model_name": "gemini-3.5-flash",
                "prompt_version": "reasoner-v1",
                "temperature": 0.0,
                "execution_id": "execution-1",
            },
        }
    )


def _context(
    registry: InMemorySourceRegistry,
    allowed_ref: str,
    **overrides: object,
) -> CompilationContext:
    values: dict[str, object] = {
        "source_registry": registry,
        "world_snapshot_id": "world:access-13",
        "owner_scope": SCOPE,
        "allowed_source_refs": frozenset({allowed_ref}),
        "risk_class": RiskClass.HIGH,
        "allow_historical": False,
    }
    values.update(overrides)
    return CompilationContext(**values)  # type: ignore[arg-type]


def test_current_allowed_ref_resolves_to_a_canonical_source_record() -> None:
    registry, _, current_ref, _ = _registry()

    report = DeterministicDraftValidator().validate(
        _draft(current_ref),
        _context(registry, current_ref),
    )

    assert report.disposition is None
    assert report.findings == []
    assert report.resolved_dependencies[0].proposed_ref == current_ref
    assert report.resolved_dependencies[0].canonical_ref == current_ref
    assert report.resolved_dependencies[0].artifact_type == "POLICY"
    assert report.resolved_dependencies[0].fragment_hash


def test_snapshot_relative_shorthand_is_resolved_but_never_kept_as_provenance() -> None:
    registry, _, current_ref, _ = _registry()
    current = SourceRef.parse(current_ref)
    shorthand = str(current.model_copy(update={"representation_id": None}))

    report = DeterministicDraftValidator().validate(
        _draft(shorthand),
        _context(registry, shorthand),
    )

    assert report.disposition is None
    assert report.resolved_dependencies[0].proposed_ref == shorthand
    assert report.resolved_dependencies[0].canonical_ref == current_ref


@pytest.mark.parametrize(
    ("source_ref", "expected_code"),
    [
        (
            "policy:invented@v13!rep-invented#section/7.3",
            "UNKNOWN_SOURCE_ARTIFACT",
        ),
        (
            "policy:access@v13!rep-invented#$.training",
            "UNKNOWN_PARSED_REPRESENTATION",
        ),
    ],
)
def test_unknown_refs_are_fatal_and_never_repaired(
    source_ref: str,
    expected_code: str,
) -> None:
    registry, _, current_ref, _ = _registry()

    report = DeterministicDraftValidator().validate(
        _draft(source_ref),
        _context(registry, current_ref, allowed_source_refs=frozenset({source_ref})),
    )

    assert report.disposition is CompilationDisposition.REJECTED_INVALID_REFERENCE
    assert [(finding.stage, finding.code) for finding in report.findings] == [
        (ValidationStage.REFERENCE, expected_code)
    ]
    assert report.resolved_dependencies == []


def test_current_but_request_unauthorized_ref_is_rejected_before_resolution() -> None:
    registry, _, current_ref, _ = _registry()

    report = DeterministicDraftValidator().validate(
        _draft(current_ref),
        _context(registry, current_ref, allowed_source_refs=frozenset()),
    )

    assert report.disposition is CompilationDisposition.REJECTED_INVALID_REFERENCE
    assert report.findings[0].stage is ValidationStage.SCOPE
    assert report.findings[0].code == "UNAUTHORIZED_SOURCE_REFERENCE"


def test_cross_scope_context_is_rejected_even_if_allowlist_contains_the_ref() -> None:
    registry, _, current_ref, _ = _registry()

    report = DeterministicDraftValidator().validate(
        _draft(current_ref),
        _context(registry, current_ref, owner_scope="tenant:other"),
    )

    assert report.disposition is CompilationDisposition.REJECTED_INVALID_REFERENCE
    assert report.findings[0].stage is ValidationStage.SCOPE
    assert report.findings[0].code == "UNAUTHORIZED_SOURCE_REFERENCE"


def test_stale_revision_has_a_distinct_disposition() -> None:
    registry, old_ref, _, _ = _registry()

    report = DeterministicDraftValidator().validate(
        _draft(old_ref),
        _context(registry, old_ref),
    )

    assert report.disposition is CompilationDisposition.REJECTED_STALE_SOURCE
    assert report.findings[0].stage is ValidationStage.TEMPORAL
    assert report.findings[0].code == "STALE_SOURCE_REFERENCE"
    assert report.resolved_dependencies == []


def test_historical_reasoning_is_explicit_and_remains_tagged() -> None:
    registry, old_ref, _, _ = _registry()

    report = DeterministicDraftValidator().validate(
        _draft(old_ref),
        _context(registry, old_ref, allow_historical=True),
    )

    assert report.disposition is None
    assert report.resolved_dependencies[0].is_historical is True


def test_malformed_ref_is_a_deterministic_reference_finding() -> None:
    registry, _, current_ref, _ = _registry()

    report = DeterministicDraftValidator().validate(
        _draft("human filename section 7"),
        _context(
            registry,
            current_ref,
            allowed_source_refs=frozenset({"human filename section 7"}),
        ),
    )

    assert report.disposition is CompilationDisposition.REJECTED_INVALID_REFERENCE
    assert report.findings[0].stage is ValidationStage.REFERENCE
    assert report.findings[0].code == "SOURCE_REF_INVALID"
