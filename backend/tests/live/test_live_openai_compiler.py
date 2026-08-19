from __future__ import annotations

import os
from decimal import Decimal

import pytest

from app.compiler.budget import SQLiteBudgetLedger
from app.compiler.canonicalization import DeterministicCanonicalizer
from app.compiler.models import CriticReview
from app.compiler.reasoner import (
    DependencyReasoner,
    OpenAIResponsesTransport,
    openai_luna_pricing,
)
from app.compiler.validation import DeterministicDraftValidator
from tests.live.compiler_live_fixture import build_live_access_case


pytestmark = pytest.mark.live


def test_live_openai_compiles_a_multi_source_decision_within_budget(tmp_path) -> None:  # type: ignore[no-untyped-def]
    if not os.environ.get("OPENAI_API_KEY"):
        pytest.skip("OPENAI_API_KEY is required for live OpenAI evidence")
    from openai import OpenAI

    tools, context, expected_refs, request = build_live_access_case()
    ledger = SQLiteBudgetLedger(
        tmp_path / "openai-budget.db",
        limit_usd=Decimal("10"),
    )
    transport = OpenAIResponsesTransport(
        client=OpenAI(),
        budget=ledger,
        pricing=openai_luna_pricing(),
        max_input_tokens=250_000,
        max_output_tokens=8_192,
    )
    draft = DependencyReasoner(
        transport,
        model_name="gpt-5.6-luna",
        prompt_version="reasoner-v1",
    ).propose(request, tools)

    proposed_refs = {
        dependency.source_ref
        for claim in draft.claims
        for dependency in claim.dependencies
    } | {dependency.source_ref for dependency in draft.decision_dependencies}
    assert proposed_refs == expected_refs

    validation = DeterministicDraftValidator().validate(draft, context)
    assert validation.disposition is None, validation.findings
    compilation = DeterministicCanonicalizer(
        compiler_version="sdc-1",
        validation_policy_version="validation-v1",
    ).compile(draft, context, validation, CriticReview())

    assert len(compilation.canonical_claims) >= 2
    assert {
        edge.source_id
        for edge in compilation.canonical_edges
        if edge.source_kind == "SOURCE_FRAGMENT"
    } == expected_refs
    budget = ledger.snapshot()
    assert Decimal("0") < budget.spent_usd <= Decimal("10")
