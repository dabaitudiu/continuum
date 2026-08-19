from __future__ import annotations

import inspect
from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal
from pathlib import Path

import pytest
from app.compiler import budget as budget_module
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
    cache_write_usd_per_million=Decimal("0.25"),
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


def test_pricing_charges_cache_writes_at_the_explicit_premium() -> None:
    cost = LUNA_PRICING.cost(
        ModelUsage(
            input_tokens=1_000_000,
            cached_input_tokens=200_000,
            cache_write_tokens=300_000,
            output_tokens=1_000_000,
        )
    )

    assert cost == Decimal("1.379000000")


def test_cached_reads_and_writes_must_fit_inside_total_input() -> None:
    with pytest.raises(ValueError):
        ModelUsage(
            input_tokens=100,
            cached_input_tokens=60,
            cache_write_tokens=50,
            output_tokens=0,
        )


def test_reservation_rejects_before_spend_can_exceed_ten_dollar_cap(
    tmp_path: Path,
) -> None:
    ledger = SQLiteBudgetLedger(tmp_path / "budget.db", limit_usd=Decimal(10))
    six_dollars = ModelPricing(
        provider="OPENAI",
        model_name="test-model",
        input_usd_per_million=Decimal(6),
        cached_input_usd_per_million=Decimal(6),
        cache_write_usd_per_million=Decimal(6),
        output_usd_per_million=Decimal(6),
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
    ledger.close()


def test_settlement_charges_actual_usage_and_releases_unused_reservation(
    tmp_path: Path,
) -> None:
    ledger = SQLiteBudgetLedger(tmp_path / "budget.db", limit_usd=Decimal(10))
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
    ledger.close()


def test_settlement_is_idempotent_for_the_same_actual_usage(tmp_path: Path) -> None:
    ledger = SQLiteBudgetLedger(tmp_path / "budget.db", limit_usd=Decimal(10))
    usage = ModelUsage(input_tokens=10_000, output_tokens=1_000)
    ledger.reserve("call-1", pricing=LUNA_PRICING, maximum_usage=usage)

    first = ledger.settle("call-1", actual_usage=usage)
    second = ledger.settle("call-1", actual_usage=usage)

    assert first == second
    assert ledger.snapshot().settled_calls == 1
    ledger.close()


@pytest.mark.parametrize(
    ("settled", "expected_code"),
    [
        (False, "MODEL_BUDGET_CALL_IN_PROGRESS"),
        (True, "MODEL_BUDGET_CALL_ALREADY_SETTLED"),
    ],
)
def test_call_id_grants_execution_ownership_exactly_once(
    tmp_path: Path,
    settled: bool,
    expected_code: str,
) -> None:
    with SQLiteBudgetLedger(
        tmp_path / "budget.db",
        limit_usd=Decimal(10),
    ) as ledger:
        usage = ModelUsage(input_tokens=10_000, output_tokens=1_000)
        ledger.reserve("call-1", pricing=LUNA_PRICING, maximum_usage=usage)
        if settled:
            ledger.settle("call-1", actual_usage=usage)

        with pytest.raises(BudgetError) as raised:
            ledger.reserve("call-1", pricing=LUNA_PRICING, maximum_usage=usage)

        assert raised.value.code == expected_code


def test_unknown_outcome_keeps_worst_case_cost_reserved(tmp_path: Path) -> None:
    with SQLiteBudgetLedger(
        tmp_path / "budget.db",
        limit_usd=Decimal(10),
    ) as ledger:
        usage = ModelUsage(input_tokens=1_000_000, output_tokens=1_000_000)
        ledger.reserve("call-1", pricing=LUNA_PRICING, maximum_usage=usage)
        unknown = ledger.mark_unknown("call-1")

        assert unknown.status == "UNKNOWN"
        assert ledger.snapshot().reserved_usd == LUNA_PRICING.cost(usage)
        with pytest.raises(BudgetError) as raised:
            ledger.reserve("call-1", pricing=LUNA_PRICING, maximum_usage=usage)
        assert raised.value.code == "MODEL_BUDGET_CALL_OUTCOME_UNKNOWN"


def test_budget_state_survives_process_reopen(tmp_path: Path) -> None:
    path = tmp_path / "budget.db"
    first = SQLiteBudgetLedger(path, limit_usd=Decimal(10))
    usage = ModelUsage(input_tokens=100_000, output_tokens=10_000)
    first.reserve("call-1", pricing=LUNA_PRICING, maximum_usage=usage)
    first.settle("call-1", actual_usage=usage)
    first.close()

    reopened = SQLiteBudgetLedger(path, limit_usd=Decimal(10))

    assert reopened.snapshot().spent_usd == Decimal("0.032000000")
    assert reopened.snapshot().settled_calls == 1
    reopened.close()


def test_concurrent_reservations_cannot_race_past_limit(tmp_path: Path) -> None:
    path = tmp_path / "budget.db"
    pricing = ModelPricing(
        provider="OPENAI",
        model_name="test-model",
        input_usd_per_million=Decimal(6),
        cached_input_usd_per_million=Decimal(6),
        cache_write_usd_per_million=Decimal(6),
        output_usd_per_million=Decimal(6),
        pricing_version="test-v1",
    )

    def reserve(call_id: str) -> str:
        ledger = SQLiteBudgetLedger(path, limit_usd=Decimal(10))
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


def test_usage_summary_includes_every_settled_attempt_for_a_namespace(
    tmp_path: Path,
) -> None:
    with SQLiteBudgetLedger(
        tmp_path / "budget.db",
        limit_usd=Decimal(10),
    ) as ledger:
        first = ModelUsage(
            input_tokens=1_000,
            cached_input_tokens=100,
            cache_write_tokens=200,
            output_tokens=50,
        )
        second = ModelUsage(
            input_tokens=2_000,
            cached_input_tokens=300,
            cache_write_tokens=400,
            output_tokens=75,
        )
        for call_id, usage in (
            ("run-a:reasoner:1", first),
            ("run-a:reasoner:2", second),
            ("run-b:reasoner:1", first),
        ):
            ledger.reserve(call_id, pricing=LUNA_PRICING, maximum_usage=usage)
            ledger.settle(call_id, actual_usage=usage)

        summary = ledger.settled_usage("run-a:")

    assert summary.usage == ModelUsage(
        input_tokens=3_000,
        cached_input_tokens=400,
        cache_write_tokens=600,
        output_tokens=125,
    )
    assert summary.settled_calls == 2
    assert summary.actual_cost_usd == LUNA_PRICING.cost(first) + LUNA_PRICING.cost(
        second
    )


def test_usage_summary_can_isolate_reasoner_and_critic_stages(
    tmp_path: Path,
) -> None:
    with SQLiteBudgetLedger(
        tmp_path / "budget.db",
        limit_usd=Decimal(10),
    ) as ledger:
        summarize_stage = getattr(ledger, "settled_usage_by_stage", None)
        assert summarize_stage is not None
        reasoner_usage = ModelUsage(
            input_tokens=1_000,
            cache_write_tokens=800,
            output_tokens=50,
        )
        critic_usage = ModelUsage(
            input_tokens=2_000,
            cached_input_tokens=500,
            cache_write_tokens=1_000,
            output_tokens=75,
        )
        for call_id, usage in (
            ("experiment:case-1:run:0:reasoner:1", reasoner_usage),
            ("experiment:case-1:run:0:critic:1", critic_usage),
            ("other:case-1:run:0:critic:1", reasoner_usage),
        ):
            ledger.reserve(call_id, pricing=LUNA_PRICING, maximum_usage=usage)
            ledger.settle(call_id, actual_usage=usage)

        critic = summarize_stage("experiment:", "critic")

    assert critic.settled_calls == 1
    assert critic.usage == critic_usage
    assert critic.actual_cost_usd == LUNA_PRICING.cost(critic_usage)


def test_scoped_budget_rejects_incremental_experiment_exposure_before_send(
    tmp_path: Path,
) -> None:
    scoped_type = getattr(budget_module, "ScopedBudgetLedger", None)
    assert scoped_type is not None
    pricing = ModelPricing(
        provider="OPENAI",
        model_name="test-model",
        input_usd_per_million=Decimal(1),
        cached_input_usd_per_million=Decimal(1),
        cache_write_usd_per_million=Decimal(1),
        output_usd_per_million=Decimal(1),
        pricing_version="test-v1",
    )
    maximum = ModelUsage(input_tokens=200_000, output_tokens=0)
    actual = ModelUsage(input_tokens=100_000, output_tokens=0)
    with SQLiteBudgetLedger(
        tmp_path / "budget.db",
        limit_usd=Decimal(10),
    ) as ledger:
        scoped = scoped_type(
            ledger,
            call_id_prefix="experiment-1:",
            limit_usd=Decimal("0.25"),
        )
        scoped.reserve(
            "experiment-1:case-1:reasoner:1",
            pricing=pricing,
            maximum_usage=maximum,
        )
        scoped.settle(
            "experiment-1:case-1:reasoner:1",
            actual_usage=actual,
        )

        with pytest.raises(BudgetError) as raised:
            scoped.reserve(
                "experiment-1:case-2:reasoner:1",
                pricing=pricing,
                maximum_usage=maximum,
            )

        assert raised.value.code == "EXPERIMENT_BUDGET_EXHAUSTED"
        assert scoped.snapshot().spent_usd == Decimal("0.100000000")
        assert scoped.snapshot().remaining_usd == Decimal("0.150000000")
        assert ledger.snapshot().settled_calls == 1


def test_scoped_budget_enforces_absolute_model_post_ceiling(tmp_path: Path) -> None:
    scoped_type = getattr(budget_module, "ScopedBudgetLedger", None)
    assert scoped_type is not None
    assert "max_calls" in inspect.signature(scoped_type).parameters
    usage = ModelUsage(input_tokens=1_000, output_tokens=10)
    with SQLiteBudgetLedger(
        tmp_path / "budget.db",
        limit_usd=Decimal(10),
    ) as ledger:
        scoped = scoped_type(
            ledger,
            call_id_prefix="experiment-1:",
            limit_usd=Decimal(1),
            max_calls=1,
        )
        scoped.reserve(
            "experiment-1:case-1:reasoner:1",
            pricing=LUNA_PRICING,
            maximum_usage=usage,
        )
        scoped.settle(
            "experiment-1:case-1:reasoner:1",
            actual_usage=usage,
        )

        with pytest.raises(BudgetError) as raised:
            scoped.reserve(
                "experiment-1:case-2:reasoner:1",
                pricing=LUNA_PRICING,
                maximum_usage=usage,
            )

    assert raised.value.code == "EXPERIMENT_CALL_LIMIT_EXHAUSTED"
