from __future__ import annotations

import pytest
from app.compiler.models import (
    ClaimDraft,
    ClaimType,
    CompilationDisposition,
    CompilationResult,
    DecisionDraft,
    DependencyRef,
    DependencyRelation,
    Materiality,
    ModelMetadata,
    UnresolvedQuestion,
)
from pydantic import ValidationError


def _dependency(**overrides: object) -> dict[str, object]:
    value: dict[str, object] = {
        "source_ref": "policy:security@v13!rep-13#section/7.3",
        "relation": "GOVERNED_BY",
        "materiality": "CRITICAL",
        "purpose": "Defines the applicable control",
    }
    value.update(overrides)
    return value


def _claim(**overrides: object) -> dict[str, object]:
    value: dict[str, object] = {
        "claim_local_id": "c1",
        "claim_type": "RULE",
        "statement": "Privileged access requires current security training.",
        "dependencies": [_dependency()],
        "derived_from_claims": [],
        "materiality": "CRITICAL",
        "confidence": 0.97,
    }
    value.update(overrides)
    return value


def _draft(**overrides: object) -> dict[str, object]:
    value: dict[str, object] = {
        "request_id": "request-1",
        "decision_type": "PRIVILEGED_ACCESS_REVIEW",
        "proposed_outcome": "APPROVED",
        "claims": [_claim()],
        "decision_dependencies": [_dependency(purpose="Governs approval")],
        "unresolved_questions": [],
        "rationale_summary": "The current policy requirements are satisfied.",
        "model_metadata": {
            "provider": "GOOGLE",
            "model_name": "gemini-3.5-flash",
            "prompt_version": "reasoner-v1",
            "temperature": 0.0,
            "execution_id": "execution-1",
        },
    }
    value.update(overrides)
    return value


def test_decision_draft_parses_the_full_typed_ir() -> None:
    draft = DecisionDraft.model_validate(_draft())

    assert draft.claims[0].claim_type is ClaimType.RULE
    assert draft.claims[0].dependencies[0].relation is DependencyRelation.GOVERNED_BY
    assert draft.claims[0].materiality is Materiality.CRITICAL
    assert draft.model_metadata.model_name == "gemini-3.5-flash"


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("request_id", ""),
        ("decision_type", " "),
        ("proposed_outcome", ""),
        ("rationale_summary", ""),
    ],
)
def test_decision_draft_rejects_blank_auditable_fields(
    field: str,
    value: str,
) -> None:
    with pytest.raises(ValidationError):
        DecisionDraft.model_validate(_draft(**{field: value}))


def test_decision_draft_rejects_duplicate_local_claim_ids() -> None:
    duplicate = _claim(statement="A different statement with the same local id.")

    with pytest.raises(ValidationError, match="duplicate claim_local_id: c1"):
        DecisionDraft.model_validate(_draft(claims=[_claim(), duplicate]))


@pytest.mark.parametrize("confidence", [-0.01, 1.01])
def test_claim_rejects_confidence_outside_the_closed_unit_interval(
    confidence: float,
) -> None:
    with pytest.raises(ValidationError):
        ClaimDraft.model_validate(_claim(confidence=confidence))


def test_ir_rejects_unknown_fields_instead_of_silently_storing_model_output() -> None:
    with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
        DecisionDraft.model_validate(_draft(hidden_chain_of_thought="secret"))


def test_blocking_unresolved_question_is_explicit_and_typed() -> None:
    draft = DecisionDraft.model_validate(
        _draft(
            unresolved_questions=[
                {
                    "question": "Is training still current?",
                    "required_source_type": "STRUCTURED_RECORD",
                    "blocking": True,
                }
            ]
        )
    )

    assert draft.unresolved_questions == [
        UnresolvedQuestion(
            question="Is training still current?",
            required_source_type="STRUCTURED_RECORD",
            blocking=True,
        )
    ]


def test_ir_enums_are_closed_contracts() -> None:
    with pytest.raises(ValidationError):
        DependencyRef.model_validate(_dependency(relation="MENTIONED_IN"))
    with pytest.raises(ValidationError):
        ClaimDraft.model_validate(_claim(materiality="OPTIONAL"))


def test_compilation_result_serializes_the_specified_disposition() -> None:
    result = CompilationResult(
        compilation_id="compilation-1",
        request_id="request-1",
        status=CompilationDisposition.REJECTED_SCHEMA,
        compiler_version="sdc-1",
        validation_policy_version="validation-v1",
    )

    assert result.model_dump(mode="json") == {
        "compilation_id": "compilation-1",
        "request_id": "request-1",
        "status": "REJECTED_SCHEMA",
        "decision_candidate": None,
        "canonical_claims": [],
        "canonical_edges": [],
        "validation_findings": [],
        "critic_findings": [],
        "contradictions": [],
        "compiler_version": "sdc-1",
        "validation_policy_version": "validation-v1",
        "compilation_hash": None,
        "model_metadata": None,
        "critic_model_metadata": None,
        "executed_stages": [],
    }


def test_value_objects_are_immutable_after_validation() -> None:
    metadata = ModelMetadata(
        provider="GOOGLE",
        model_name="gemini-3.5-flash",
        prompt_version="reasoner-v1",
        temperature=0.0,
        execution_id="execution-1",
    )

    with pytest.raises(ValidationError):
        metadata.model_name = "different"  # type: ignore[misc]
