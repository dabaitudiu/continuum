from __future__ import annotations

import os

import pytest

from app.compiler.canonicalization import DeterministicCanonicalizer
from app.compiler.models import CriticReview
from app.compiler.prompts import REASONER_PROMPT_VERSION
from app.compiler.reasoner import AdkGeminiTransport, DependencyReasoner
from app.compiler.validation import DeterministicDraftValidator
from tests.live.compiler_live_fixture import build_live_access_case


pytestmark = pytest.mark.live


def test_live_gemini_compiles_a_multi_source_decision() -> None:
    using_api_key = bool(
        os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    )
    using_vertex = (
        os.environ.get("GOOGLE_GENAI_USE_VERTEXAI", "").upper() == "TRUE"
        and bool(os.environ.get("GOOGLE_CLOUD_PROJECT"))
        and bool(os.environ.get("GOOGLE_CLOUD_LOCATION"))
    )
    if not (using_api_key or using_vertex):
        pytest.skip("Gemini API key or configured Vertex credentials are required")

    tools, context, expected_refs, request = build_live_access_case()
    model_name = os.environ.get("CONTINUUM_GEMINI_MODEL", "gemini-3.5-flash")
    draft = DependencyReasoner(
        AdkGeminiTransport(),
        model_name=model_name,
        prompt_version=REASONER_PROMPT_VERSION,
    ).propose(request, tools)

    proposed_refs = {
        dependency.source_ref
        for claim in draft.claims
        for dependency in claim.dependencies
    } | {dependency.source_ref for dependency in draft.decision_dependencies}
    assert proposed_refs == expected_refs
    assert draft.model_metadata.provider == "GOOGLE"

    validation = DeterministicDraftValidator().validate(draft, context)
    assert validation.disposition is None, validation.findings
    compilation = DeterministicCanonicalizer(
        compiler_version="sdc-1",
        validation_policy_version="validation-v1",
    ).compile(draft, context, validation, CriticReview())
    assert {
        edge.source_id
        for edge in compilation.canonical_edges
        if edge.source_kind == "SOURCE_FRAGMENT"
    } == expected_refs
