from __future__ import annotations

from datetime import UTC, datetime
from time import perf_counter

from app.compiler.canonicalization import DeterministicCanonicalizer
from app.compiler.context import CompilationContext, RiskClass
from app.compiler.models import CriticReview, DecisionDraft
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


NOW = datetime(2026, 8, 19, 11, 0, tzinfo=UTC)


def _environment(value: dict[str, object]) -> tuple[CompilationContext, str]:
    artifact = Artifact(
        artifact_id="record:release",
        artifact_type=ArtifactType.RECORD,
        logical_key="release",
        owner_scope="tenant:alpha",
        trust_class=TrustClass.AUTHORITATIVE,
        source_type=SourceType.STRUCTURED_RECORD,
        authority_rank=90,
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
    registry = InMemorySourceRegistry()
    registry.add_artifact(artifact)
    registry.add_revision(ingested.revision)
    registry.add_representation(ingested.representation, ingested.fragments)
    registry.add_world_snapshot(
        WorldSnapshot(
            world_snapshot_id="world:release",
            owner_scope="tenant:alpha",
            current_revisions={artifact.artifact_id: ingested.revision.revision_id},
            current_representations={
                ingested.revision.revision_id: ingested.representation.representation_id,
            },
            created_at=NOW,
        )
    )
    source_ref = str(ingested.fragment_at("$.status").source_ref())
    return (
        CompilationContext(
            source_registry=registry,
            world_snapshot_id="world:release",
            owner_scope="tenant:alpha",
            allowed_source_refs=frozenset({source_ref}),
            risk_class=RiskClass.HIGH,
        ),
        source_ref,
    )


def _dependency(source_ref: str, purpose: str = "Primary evidence") -> dict[str, object]:
    return {
        "source_ref": source_ref,
        "relation": "SUPPORTED_BY",
        "materiality": "CRITICAL",
        "purpose": purpose,
    }


def _claim(local_id: str, source_ref: str) -> dict[str, object]:
    return {
        "claim_local_id": local_id,
        "claim_type": "FACT",
        "statement": f"Release fact {local_id}",
        "dependencies": [_dependency(source_ref)],
        "derived_from_claims": [],
        "materiality": "CRITICAL",
        "confidence": 0.98,
    }


def _draft(
    source_ref: str,
    *,
    claims: list[dict[str, object]] | None = None,
) -> DecisionDraft:
    return DecisionDraft.model_validate(
        {
            "request_id": "request-release",
            "decision_type": "PRODUCTION_RELEASE_REVIEW",
            "proposed_outcome": "APPROVED",
            "claims": claims or [_claim("c1", source_ref)],
            "decision_dependencies": [],
            "unresolved_questions": [],
            "rationale_summary": "Evidence supports release.",
            "model_metadata": {
                "provider": "GOOGLE",
                "model_name": "gemini-3.5-flash",
                "prompt_version": "reasoner-v1",
                "temperature": 0.0,
                "execution_id": "execution-1",
            },
        }
    )


def _compile(
    context: CompilationContext,
    draft: DecisionDraft,
    *,
    compiler_version: str = "sdc-1",
    policy_version: str = "validation-v1",
):  # type: ignore[no-untyped-def]
    validation = DeterministicDraftValidator().validate(draft, context)
    assert validation.disposition is None
    return DeterministicCanonicalizer(
        compiler_version=compiler_version,
        validation_policy_version=policy_version,
    ).compile(draft, context, validation, CriticReview())


def test_canonicalization_is_idempotent_and_assigns_stable_ids() -> None:
    context, source_ref = _environment({"status": "passed"})
    draft = _draft(source_ref)

    first = _compile(context, draft)
    second = _compile(context, draft)

    assert first == second
    assert first.compilation_id == f"compilation:{first.compilation_hash}"
    assert first.decision_candidate.decision_id.startswith("decision:")
    assert first.canonical_claims[0].claim_id.startswith("claim:")
    assert first.canonical_edges[0].edge_id.startswith("edge:")


def test_claim_and_dependency_input_order_does_not_change_canonical_output() -> None:
    context, source_ref = _environment({"status": "passed"})
    claims_forward = [_claim("c2", source_ref), _claim("c1", source_ref)]
    claims_reverse = list(reversed(claims_forward))

    forward = _compile(context, _draft(source_ref, claims=claims_forward))
    reverse = _compile(context, _draft(source_ref, claims=claims_reverse))

    assert forward == reverse
    assert [claim.claim_local_id for claim in forward.canonical_claims] == ["c1", "c2"]


def test_duplicate_edges_collapse_deterministically() -> None:
    context, source_ref = _environment({"status": "passed"})
    claim = _claim("c1", source_ref)
    claim["dependencies"] = [
        _dependency(source_ref, "Z purpose"),
        _dependency(source_ref, "A purpose"),
        _dependency(source_ref, "Z purpose"),
    ]

    compiled = _compile(context, _draft(source_ref, claims=[claim]))

    source_edges = [
        edge
        for edge in compiled.canonical_edges
        if edge.source_kind == "SOURCE_FRAGMENT"
    ]
    assert len(source_edges) == 1
    assert source_edges[0].purpose == "A purpose"


def test_snapshot_relative_ref_is_replaced_by_fully_qualified_provenance() -> None:
    context, source_ref = _environment({"status": "passed"})
    parsed = SourceRef.parse(source_ref)
    shorthand = str(parsed.model_copy(update={"representation_id": None}))
    shorthand_context = CompilationContext(
        source_registry=context.source_registry,
        world_snapshot_id=context.world_snapshot_id,
        owner_scope=context.owner_scope,
        allowed_source_refs=frozenset({shorthand}),
        risk_class=context.risk_class,
    )

    compiled = _compile(shorthand_context, _draft(shorthand))

    source_edge = next(
        edge
        for edge in compiled.canonical_edges
        if edge.source_kind == "SOURCE_FRAGMENT"
    )
    assert source_edge.source_id == source_ref
    assert "!" in source_edge.source_id


def test_source_content_and_compiler_policy_are_bound_into_compilation_hash() -> None:
    first_context, first_ref = _environment({"status": "passed"})
    changed_context, changed_ref = _environment({"status": "failed"})

    base = _compile(first_context, _draft(first_ref))
    changed_source = _compile(changed_context, _draft(changed_ref))
    changed_compiler = _compile(first_context, _draft(first_ref), compiler_version="sdc-2")
    changed_policy = _compile(first_context, _draft(first_ref), policy_version="validation-v2")

    assert len(
        {
            base.compilation_hash,
            changed_source.compilation_hash,
            changed_compiler.compilation_hash,
            changed_policy.compilation_hash,
        }
    ) == 4


def test_deterministic_compile_of_100_claim_proposal_completes_under_100ms() -> None:
    context, source_ref = _environment({"status": "passed"})
    draft = _draft(
        source_ref,
        claims=[_claim(f"c{index:03d}", source_ref) for index in range(100)],
    )

    started = perf_counter()
    _compile(context, draft)
    elapsed = perf_counter() - started

    assert elapsed < 0.1, f"deterministic compile took {elapsed:.4f}s"
