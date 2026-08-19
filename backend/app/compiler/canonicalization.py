from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable
from typing import Any

from app.compiler.context import CompilationContext
from app.compiler.models import (
    CanonicalClaim,
    CanonicalCompilation,
    CanonicalEdge,
    ClaimDraft,
    CriticReview,
    DecisionCandidate,
    DecisionDraft,
    DependencyRef,
    DependencyRelation,
    Materiality,
    ResolvedDependency,
    ValidationReport,
)


class DeterministicCanonicalizer:
    def __init__(
        self,
        *,
        compiler_version: str,
        validation_policy_version: str,
    ) -> None:
        if not compiler_version.strip() or not validation_policy_version.strip():
            raise ValueError("compiler and validation policy versions are required")
        self._compiler_version = compiler_version
        self._validation_policy_version = validation_policy_version

    def compile(
        self,
        draft: DecisionDraft,
        context: object,
        validation: ValidationReport,
        review: CriticReview,
    ) -> CanonicalCompilation:
        if not isinstance(context, CompilationContext):
            raise TypeError("canonicalizer requires CompilationContext")
        if validation.disposition is not None or review.disposition is not None:
            raise ValueError("only non-blocking reports can be canonicalized")

        normalized_draft = _normalized_draft(
            draft,
            validation.resolved_dependencies,
        )
        source_bindings = _source_bindings(validation.resolved_dependencies)
        compilation_hash = _sha256_json(
            {
                "compiler_version": self._compiler_version,
                "validation_policy_version": self._validation_policy_version,
                "world_snapshot_id": context.world_snapshot_id,
                "draft": normalized_draft,
                "source_bindings": source_bindings,
            }
        )
        decision_id = _stable_id("decision", compilation_hash, draft.request_id)
        claim_ids = {
            claim.claim_local_id: _stable_id(
                "claim",
                compilation_hash,
                claim.claim_local_id,
            )
            for claim in draft.claims
        }
        canonical_claims = [
            CanonicalClaim(
                claim_id=claim_ids[claim.claim_local_id],
                claim_local_id=claim.claim_local_id,
                claim_type=claim.claim_type,
                statement=claim.statement,
                materiality=claim.materiality,
                confidence=claim.confidence,
            )
            for claim in sorted(draft.claims, key=lambda value: value.claim_local_id)
        ]
        canonical_edges = _canonical_edges(
            draft,
            validation.resolved_dependencies,
            compilation_hash=compilation_hash,
            decision_id=decision_id,
            claim_ids=claim_ids,
        )
        return CanonicalCompilation(
            compilation_id=f"compilation:{compilation_hash}",
            compilation_hash=compilation_hash,
            decision_candidate=DecisionCandidate(
                decision_id=decision_id,
                decision_type=draft.decision_type,
                outcome=draft.proposed_outcome,
                rationale_summary=draft.rationale_summary,
            ),
            canonical_claims=canonical_claims,
            canonical_edges=canonical_edges,
        )


def _normalized_draft(
    draft: DecisionDraft,
    resolved_dependencies: list[ResolvedDependency],
) -> dict[str, Any]:
    canonical_refs = {
        dependency.proposed_ref: dependency.canonical_ref
        for dependency in resolved_dependencies
    }
    claims = [
        {
            "claim_local_id": claim.claim_local_id,
            "claim_type": claim.claim_type.value,
            "statement": claim.statement,
            "dependencies": _normalized_dependencies(
                claim.dependencies,
                canonical_refs,
            ),
            "derived_from_claims": sorted(claim.derived_from_claims),
            "materiality": claim.materiality.value,
            "confidence": claim.confidence,
        }
        for claim in sorted(draft.claims, key=lambda value: value.claim_local_id)
    ]
    return {
        "request_id": draft.request_id,
        "decision_type": draft.decision_type,
        "proposed_outcome": draft.proposed_outcome,
        "claims": claims,
        "decision_dependencies": _normalized_dependencies(
            draft.decision_dependencies,
            canonical_refs,
        ),
        "unresolved_questions": sorted(
            (
                question.model_dump(mode="json")
                for question in draft.unresolved_questions
            ),
            key=lambda item: (
                item["question"],
                item["required_source_type"],
                item["blocking"],
            ),
        ),
        "rationale_summary": draft.rationale_summary,
        "model_metadata": draft.model_metadata.model_dump(mode="json"),
    }


def _normalized_dependencies(
    dependencies: Iterable[DependencyRef],
    canonical_refs: dict[str, str],
) -> list[dict[str, Any]]:
    normalized = [
        {
            "source_ref": canonical_refs[dependency.source_ref],
            "relation": dependency.relation.value,
            "materiality": dependency.materiality.value,
            "purpose": dependency.purpose,
        }
        for dependency in dependencies
    ]
    selected: dict[tuple[str, str, str], dict[str, Any]] = {}
    for dependency in sorted(
        normalized,
        key=lambda item: (
            item["source_ref"],
            item["relation"],
            item["materiality"],
            item["purpose"] or "",
        ),
    ):
        key = (
            dependency["source_ref"],
            dependency["relation"],
            dependency["materiality"],
        )
        selected.setdefault(key, dependency)
    return list(selected.values())


def _source_bindings(
    dependencies: list[ResolvedDependency],
) -> list[dict[str, Any]]:
    bindings = {
        (
            dependency.canonical_ref,
            dependency.source_hash,
            dependency.fragment_hash,
        )
        for dependency in dependencies
    }
    return [
        {
            "canonical_ref": canonical_ref,
            "source_hash": source_hash,
            "fragment_hash": fragment_hash,
        }
        for canonical_ref, source_hash, fragment_hash in sorted(bindings)
    ]


def _canonical_edges(
    draft: DecisionDraft,
    dependencies: list[ResolvedDependency],
    *,
    compilation_hash: str,
    decision_id: str,
    claim_ids: dict[str, str],
) -> list[CanonicalEdge]:
    candidates: list[dict[str, Any]] = []
    for dependency in dependencies:
        target_id = (
            claim_ids[dependency.target_local_id]
            if dependency.target_kind == "CLAIM"
            else decision_id
        )
        candidates.append(
            {
                "source_kind": "SOURCE_FRAGMENT",
                "source_id": dependency.canonical_ref,
                "target_kind": dependency.target_kind,
                "target_id": target_id,
                "relation": dependency.relation,
                "materiality": dependency.materiality,
                "purpose": dependency.purpose,
            }
        )
    for claim in draft.claims:
        for source_claim_local_id in claim.derived_from_claims:
            candidates.append(
                {
                    "source_kind": "CLAIM",
                    "source_id": claim_ids[source_claim_local_id],
                    "target_kind": "CLAIM",
                    "target_id": claim_ids[claim.claim_local_id],
                    "relation": DependencyRelation.DERIVED_FROM,
                    "materiality": claim.materiality,
                    "purpose": "Derived claim provenance",
                }
            )
        candidates.append(
            {
                "source_kind": "CLAIM",
                "source_id": claim_ids[claim.claim_local_id],
                "target_kind": "DECISION",
                "target_id": decision_id,
                "relation": DependencyRelation.REQUIRES,
                "materiality": claim.materiality,
                "purpose": "Claim contributes to decision",
            }
        )

    selected: dict[tuple[str, str, str, str, str, str], dict[str, Any]] = {}
    for candidate in sorted(candidates, key=_edge_sort_key):
        key = _edge_identity(candidate)
        selected.setdefault(key, candidate)

    edges: list[CanonicalEdge] = []
    for key, candidate in sorted(selected.items()):
        edge_digest = _sha256_text(
            f"{compilation_hash}:{json.dumps(key, separators=(',', ':'))}"
        )
        edges.append(
            CanonicalEdge(
                edge_id=f"edge:{edge_digest[:32]}",
                **candidate,
            )
        )
    return edges


def _edge_identity(candidate: dict[str, Any]) -> tuple[str, str, str, str, str, str]:
    return (
        candidate["source_kind"],
        candidate["source_id"],
        candidate["target_kind"],
        candidate["target_id"],
        candidate["relation"].value,
        candidate["materiality"].value,
    )


def _edge_sort_key(candidate: dict[str, Any]) -> tuple[str, ...]:
    return (*_edge_identity(candidate), candidate["purpose"] or "")


def _stable_id(prefix: str, compilation_hash: str, local_id: str) -> str:
    return f"{prefix}:{_sha256_text(f'{compilation_hash}:{prefix}:{local_id}')[:32]}"


def _sha256_json(value: Any) -> str:
    encoded = json.dumps(
        value,
        sort_keys=True,
        ensure_ascii=False,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()
