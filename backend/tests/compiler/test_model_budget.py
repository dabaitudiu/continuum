from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal
from pathlib import Path

import pytest

from app.compiler.budget import (
    BudgetError,
    ModelPricing,
    ModelUsage,
    SQLiteBudgetLedger,
)


LUNA_PRICING = ModelPricing(
    provider="OPENAI",
    model_name="gpt-5.6-luna",
    input_usd_per_million=Decimal("0.20"),
    cached_input_usd_per_million=Decimal("0.02"),
    output_usd_per_million=Decimal("1.20"),
    pricing_version="openai-2026-08-19",
)


def test_pricing_charges_cached_input_at_its_distinct_rate() -> None:
    cost = LUNA_PRICING.cost(
        ModelUsage(
            input_tokens=1_000_000,
            cached_input_tokens=400_000,
            output_tokens=1_000_000,
        )
    )

    assert cost == Decimal("1.328000000")


def test_reservation_rejects_before_spend_can_exceed_ten_dollar_cap(
    tmp_path: Path,
) -> None:
    ledger = SQLiteBudgetLedger(tmp_path / "budget.db", limit_usd=Decimal("10"))
    six_dollars = ModelPricing(
        provider="OPENAI",
        model_name="test-model",
        input_usd_per_million=Decimal("6"),
        cached_input_usd_per_million=Decimal("6"),
        output_usd_per_million=Decimal("6"),
        pricing_version="test-v1",
    )
    ledger.reserve(
        "call-1",
        pricing=six_dollars,
        maximum_usage=ModelUsage(input_tokens=1_000_000, output_tokens=0),
    )

    with pytest.raises(BudgetError) as raised:
        ledger.reserve(
            "call-2",
            pricing=six_dollars,
            maximum_usage=ModelUsage(input_tokens=1_000_000, output_tokens=0),
        )

    assert raised.value.code == "MODEL_BUDGET_EXHAUSTED"
    assert ledger.snapshot().reserved_usd == Decimal("6.000000000")
    assert ledger.snapshot().spent_usd == Decimal("0E-9")


def test_settlement_charges_actual_usage_and_releases_unused_reservation(
    tmp_path: Path,
) -> None:
    ledger = SQLiteBudgetLedger(tmp_path / "budget.db", limit_usd=Decimal("10"))
    ledger.reserve(
        "call-1",
        pricing=LUNA_PRICING,
        maximum_usage=ModelUsage(input_tokens=1_000_000, output_tokens=1_000_000),
    )

    record = ledger.settle(
        "call-1",
        actual_usage=ModelUsage(input_tokens=100_000, output_tokens=10_000),
    )

    assert record.actual_cost_usd == Decimal("0.032000000")
    assert ledger.snapshot().spent_usd == Decimal("0.032000000")
    assert ledger.snapshot().reserved_usd == Decimal("0E-9")
    assert ledger.snapshot().remaining_usd == Decimal("9.968000000")


def test_settlement_is_idempotent_for_the_same_actual_usage(tmp_path: Path) -> None:
    ledger = SQLiteBudgetLedger(tmp_path / "budget.db", limit_usd=Decimal("10"))
    usage = ModelUsage(input_tokens=10_000, output_tokens=1_000)
    ledger.reserve("call-1", pricing=LUNA_PRICING, maximum_usage=usage)

    first = ledger.settle("call-1", actual_usage=usage)
    second = ledger.settle("call-1", actual_usage=usage)

    assert first == second
    assert ledger.snapshot().settled_calls == 1


def test_budget_state_survives_process_reopen(tmp_path: Path) -> None:
    path = tmp_path / "budget.db"
    first = SQLiteBudgetLedger(path, limit_usd=Decimal("10"))
    usage = ModelUsage(input_tokens=100_000, output_tokens=10_000)
    first.reserve("call-1", pricing=LUNA_PRICING, maximum_usage=usage)
    first.settle("call-1", actual_usage=usage)
    first.close()

    reopened = SQLiteBudgetLedger(path, limit_usd=Decimal("10"))

    assert reopened.snapshot().spent_usd == Decimal("0.032000000")
    assert reopened.snapshot().settled_calls == 1


def test_concurrent_reservations_cannot_race_past_limit(tmp_path: Path) -> None:
    path = tmp_path / "budget.db"
    pricing = ModelPricing(
        provider="OPENAI",
        model_name="test-model",
        input_usd_per_million=Decimal("6"),
        cached_input_usd_per_million=Decimal("6"),
        output_usd_per_million=Decimal("6"),
        pricing_version="test-v1",
    )

    def reserve(call_id: str) -> str:
        ledger = SQLiteBudgetLedger(path, limit_usd=Decimal("10"))
        try:
            ledger.reserve(
                call_id,
                pricing=pricing,
                maximum_usage=ModelUsage(input_tokens=1_000_000, output_tokens=0),
            )
            return "RESERVED"
        except BudgetError as error:
            return error.code
        finally:
            ledger.close()

    with ThreadPoolExecutor(max_workers=2) as pool:
        outcomes = sorted(pool.map(reserve, ["call-a", "call-b"]))

    assert outcomes == ["MODEL_BUDGET_EXHAUSTED", "RESERVED"]
