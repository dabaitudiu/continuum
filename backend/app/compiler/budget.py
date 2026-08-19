from __future__ import annotations

import sqlite3
from decimal import ROUND_CEILING, Decimal
from pathlib import Path
from threading import RLock
from typing import Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

_NINE_PLACES = Decimal("0.000000001")
_NANODOLLARS = Decimal(1000000000)
_MILLION = Decimal(1000000)


class BudgetError(Exception):
    def __init__(self, code: str, message: str) -> None:
        self.code = code
        self.message = message
        super().__init__(f"{code}: {message}")


class _Value(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class ModelUsage(_Value):
    input_tokens: int = Field(ge=0)
    cached_input_tokens: int = Field(default=0, ge=0)
    output_tokens: int = Field(default=0, ge=0)

    @model_validator(mode="after")
    def _cached_tokens_are_part_of_input(self) -> ModelUsage:
        if self.cached_input_tokens > self.input_tokens:
            raise ValueError("cached input tokens cannot exceed input tokens")
        return self


class ModelPricing(_Value):
    provider: str = Field(min_length=1, max_length=64)
    model_name: str = Field(min_length=1, max_length=128)
    input_usd_per_million: Decimal = Field(ge=0)
    cached_input_usd_per_million: Decimal = Field(ge=0)
    output_usd_per_million: Decimal = Field(ge=0)
    pricing_version: str = Field(min_length=1, max_length=128)

    def cost(self, usage: ModelUsage) -> Decimal:
        uncached_input = usage.input_tokens - usage.cached_input_tokens
        cost = (
            Decimal(uncached_input) * self.input_usd_per_million
            + Decimal(usage.cached_input_tokens) * self.cached_input_usd_per_million
            + Decimal(usage.output_tokens) * self.output_usd_per_million
        ) / _MILLION
        return cost.quantize(_NINE_PLACES, rounding=ROUND_CEILING)


class BudgetReservation(_Value):
    call_id: str
    pricing: ModelPricing
    maximum_usage: ModelUsage
    reserved_cost_usd: Decimal
    status: str


class BudgetSettlement(_Value):
    call_id: str
    pricing: ModelPricing
    maximum_usage: ModelUsage
    actual_usage: ModelUsage
    reserved_cost_usd: Decimal
    actual_cost_usd: Decimal
    status: str = "SETTLED"


class BudgetSnapshot(_Value):
    limit_usd: Decimal
    spent_usd: Decimal
    reserved_usd: Decimal
    remaining_usd: Decimal
    settled_calls: int
    reserved_calls: int


class SQLiteBudgetLedger:
    """Durable reservation ledger that prevents concurrent overspend."""

    def __init__(self, path: Path, *, limit_usd: Decimal) -> None:
        if limit_usd <= 0:
            raise ValueError("model budget limit must be positive")
        self._path = path
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._connection = sqlite3.connect(
            path,
            timeout=30,
            isolation_level=None,
            check_same_thread=False,
        )
        self._connection.row_factory = sqlite3.Row
        self._lock = RLock()
        self._limit_nano = _to_nano(limit_usd)
        self._initialize()

    def close(self) -> None:
        with self._lock:
            self._connection.close()

    def __enter__(self) -> Self:
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:  # type: ignore[no-untyped-def]
        self.close()

    def reserve(
        self,
        call_id: str,
        *,
        pricing: ModelPricing,
        maximum_usage: ModelUsage,
    ) -> BudgetReservation:
        if not call_id.strip():
            raise ValueError("call_id must be non-empty")
        reserved_nano = _to_nano(pricing.cost(maximum_usage))
        with self._transaction():
            existing = self._connection.execute(
                "SELECT * FROM model_budget_calls WHERE call_id = ?",
                (call_id,),
            ).fetchone()
            if existing is not None:
                reservation = _reservation_from_row(existing)
                if (
                    reservation.pricing != pricing
                    or reservation.maximum_usage != maximum_usage
                ):
                    raise BudgetError(
                        "MODEL_BUDGET_CALL_CONFLICT",
                        f"call id was reused with different budget inputs: {call_id}",
                    )
                code = {
                    "SETTLED": "MODEL_BUDGET_CALL_ALREADY_SETTLED",
                    "UNKNOWN": "MODEL_BUDGET_CALL_OUTCOME_UNKNOWN",
                }.get(reservation.status, "MODEL_BUDGET_CALL_IN_PROGRESS")
                raise BudgetError(
                    code,
                    f"model call id is not available for another execution: {call_id}",
                )

            totals = self._totals_locked()
            if (
                totals["spent_nano"] + totals["reserved_nano"] + reserved_nano
                > self._limit_nano
            ):
                raise BudgetError(
                    "MODEL_BUDGET_EXHAUSTED",
                    "model call would exceed the configured cumulative budget",
                )
            self._connection.execute(
                """
                INSERT INTO model_budget_calls (
                    call_id, provider, model_name, pricing_version,
                    input_rate, cached_input_rate, output_rate,
                    maximum_usage_json, reserved_nano, status
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'RESERVED')
                """,
                (
                    call_id,
                    pricing.provider,
                    pricing.model_name,
                    pricing.pricing_version,
                    str(pricing.input_usd_per_million),
                    str(pricing.cached_input_usd_per_million),
                    str(pricing.output_usd_per_million),
                    maximum_usage.model_dump_json(),
                    reserved_nano,
                ),
            )
            row = self._connection.execute(
                "SELECT * FROM model_budget_calls WHERE call_id = ?",
                (call_id,),
            ).fetchone()
            assert row is not None
            return _reservation_from_row(row)

    def settle(
        self,
        call_id: str,
        *,
        actual_usage: ModelUsage,
    ) -> BudgetSettlement:
        with self._transaction():
            row = self._connection.execute(
                "SELECT * FROM model_budget_calls WHERE call_id = ?",
                (call_id,),
            ).fetchone()
            if row is None:
                raise BudgetError(
                    "MODEL_BUDGET_RESERVATION_NOT_FOUND",
                    f"model budget reservation does not exist: {call_id}",
                )
            pricing = _pricing_from_row(row)
            actual_nano = _to_nano(pricing.cost(actual_usage))
            if row["status"] == "SETTLED":
                existing_usage = ModelUsage.model_validate_json(
                    row["actual_usage_json"]
                )
                if existing_usage != actual_usage:
                    raise BudgetError(
                        "MODEL_BUDGET_SETTLEMENT_CONFLICT",
                        f"call was settled with different usage: {call_id}",
                    )
                return _settlement_from_row(row)
            if actual_nano > row["reserved_nano"]:
                raise BudgetError(
                    "MODEL_USAGE_EXCEEDS_RESERVATION",
                    "actual model usage exceeded its conservative reservation",
                )
            self._connection.execute(
                """
                UPDATE model_budget_calls
                SET actual_usage_json = ?, actual_nano = ?, status = 'SETTLED'
                WHERE call_id = ? AND status = 'RESERVED'
                """,
                (actual_usage.model_dump_json(), actual_nano, call_id),
            )
            settled = self._connection.execute(
                "SELECT * FROM model_budget_calls WHERE call_id = ?",
                (call_id,),
            ).fetchone()
            assert settled is not None
            return _settlement_from_row(settled)

    def mark_unknown(self, call_id: str) -> BudgetReservation:
        """Keep the worst-case reservation after an ambiguous post-send failure."""
        with self._transaction():
            row = self._connection.execute(
                "SELECT * FROM model_budget_calls WHERE call_id = ?",
                (call_id,),
            ).fetchone()
            if row is None:
                raise BudgetError(
                    "MODEL_BUDGET_RESERVATION_NOT_FOUND",
                    f"model budget reservation does not exist: {call_id}",
                )
            if row["status"] == "SETTLED":
                raise BudgetError(
                    "MODEL_BUDGET_ALREADY_SETTLED",
                    f"settled model call cannot become unknown: {call_id}",
                )
            if row["status"] == "RESERVED":
                self._connection.execute(
                    "UPDATE model_budget_calls SET status = 'UNKNOWN' WHERE call_id = ?",
                    (call_id,),
                )
            updated = self._connection.execute(
                "SELECT * FROM model_budget_calls WHERE call_id = ?",
                (call_id,),
            ).fetchone()
            assert updated is not None
            return _reservation_from_row(updated)

    def release(self, call_id: str) -> None:
        with self._transaction():
            row = self._connection.execute(
                "SELECT status FROM model_budget_calls WHERE call_id = ?",
                (call_id,),
            ).fetchone()
            if row is None:
                return
            if row["status"] != "RESERVED":
                raise BudgetError(
                    "MODEL_BUDGET_CALL_NOT_RELEASABLE",
                    f"only a definitely unsent reservation can be released: {call_id}",
                )
            self._connection.execute(
                "DELETE FROM model_budget_calls WHERE call_id = ?",
                (call_id,),
            )

    def snapshot(self) -> BudgetSnapshot:
        with self._lock:
            totals = self._totals_locked()
            committed = totals["spent_nano"] + totals["reserved_nano"]
            return BudgetSnapshot(
                limit_usd=_from_nano(self._limit_nano),
                spent_usd=_from_nano(totals["spent_nano"]),
                reserved_usd=_from_nano(totals["reserved_nano"]),
                remaining_usd=_from_nano(self._limit_nano - committed),
                settled_calls=totals["settled_calls"],
                reserved_calls=totals["reserved_calls"],
            )

    def _initialize(self) -> None:
        with self._lock:
            self._connection.executescript(
                """
                PRAGMA foreign_keys=ON;
                CREATE TABLE IF NOT EXISTS model_budget_meta (
                    singleton INTEGER PRIMARY KEY CHECK (singleton = 1),
                    limit_nano INTEGER NOT NULL
                );
                CREATE TABLE IF NOT EXISTS model_budget_calls (
                    call_id TEXT PRIMARY KEY,
                    provider TEXT NOT NULL,
                    model_name TEXT NOT NULL,
                    pricing_version TEXT NOT NULL,
                    input_rate TEXT NOT NULL,
                    cached_input_rate TEXT NOT NULL,
                    output_rate TEXT NOT NULL,
                    maximum_usage_json TEXT NOT NULL,
                    reserved_nano INTEGER NOT NULL,
                    actual_usage_json TEXT,
                    actual_nano INTEGER,
                    status TEXT NOT NULL CHECK (status IN ('RESERVED', 'UNKNOWN', 'SETTLED'))
                );
                """
            )
            self._migrate_unknown_status_support()
            row = self._connection.execute(
                "SELECT limit_nano FROM model_budget_meta WHERE singleton = 1"
            ).fetchone()
            if row is None:
                self._connection.execute(
                    "INSERT INTO model_budget_meta (singleton, limit_nano) VALUES (1, ?)",
                    (self._limit_nano,),
                )
            elif row["limit_nano"] != self._limit_nano:
                raise BudgetError(
                    "MODEL_BUDGET_LIMIT_CONFLICT",
                    "persisted model budget has a different limit",
                )

    def _migrate_unknown_status_support(self) -> None:
        row = self._connection.execute(
            "SELECT sql FROM sqlite_master WHERE type = 'table' AND name = 'model_budget_calls'"
        ).fetchone()
        if row is None or "UNKNOWN" in str(row["sql"]):
            return
        self._connection.executescript(
            """
            ALTER TABLE model_budget_calls RENAME TO model_budget_calls_legacy;
            CREATE TABLE model_budget_calls (
                call_id TEXT PRIMARY KEY,
                provider TEXT NOT NULL,
                model_name TEXT NOT NULL,
                pricing_version TEXT NOT NULL,
                input_rate TEXT NOT NULL,
                cached_input_rate TEXT NOT NULL,
                output_rate TEXT NOT NULL,
                maximum_usage_json TEXT NOT NULL,
                reserved_nano INTEGER NOT NULL,
                actual_usage_json TEXT,
                actual_nano INTEGER,
                status TEXT NOT NULL CHECK (status IN ('RESERVED', 'UNKNOWN', 'SETTLED'))
            );
            INSERT INTO model_budget_calls SELECT * FROM model_budget_calls_legacy;
            DROP TABLE model_budget_calls_legacy;
            """
        )

    def _totals_locked(self) -> dict[str, int]:
        row = self._connection.execute(
            """
            SELECT
                COALESCE(SUM(CASE WHEN status = 'SETTLED' THEN actual_nano ELSE 0 END), 0) AS spent_nano,
                COALESCE(SUM(CASE WHEN status IN ('RESERVED', 'UNKNOWN') THEN reserved_nano ELSE 0 END), 0) AS reserved_nano,
                SUM(CASE WHEN status = 'SETTLED' THEN 1 ELSE 0 END) AS settled_calls,
                SUM(CASE WHEN status IN ('RESERVED', 'UNKNOWN') THEN 1 ELSE 0 END) AS reserved_calls
            FROM model_budget_calls
            """
        ).fetchone()
        assert row is not None
        return {
            "spent_nano": int(row["spent_nano"]),
            "reserved_nano": int(row["reserved_nano"]),
            "settled_calls": int(row["settled_calls"] or 0),
            "reserved_calls": int(row["reserved_calls"] or 0),
        }

    def _transaction(self):  # type: ignore[no-untyped-def]
        return _ImmediateTransaction(self._connection, self._lock)


class _ImmediateTransaction:
    def __init__(self, connection: sqlite3.Connection, lock: RLock) -> None:
        self._connection = connection
        self._lock = lock

    def __enter__(self) -> None:
        self._lock.acquire()
        self._connection.execute("BEGIN IMMEDIATE")

    def __exit__(self, exc_type, exc_value, traceback) -> None:  # type: ignore[no-untyped-def]
        try:
            self._connection.execute("COMMIT" if exc_type is None else "ROLLBACK")
        finally:
            self._lock.release()


def _pricing_from_row(row: sqlite3.Row) -> ModelPricing:
    return ModelPricing(
        provider=row["provider"],
        model_name=row["model_name"],
        pricing_version=row["pricing_version"],
        input_usd_per_million=Decimal(row["input_rate"]),
        cached_input_usd_per_million=Decimal(row["cached_input_rate"]),
        output_usd_per_million=Decimal(row["output_rate"]),
    )


def _reservation_from_row(row: sqlite3.Row) -> BudgetReservation:
    return BudgetReservation(
        call_id=row["call_id"],
        pricing=_pricing_from_row(row),
        maximum_usage=ModelUsage.model_validate_json(row["maximum_usage_json"]),
        reserved_cost_usd=_from_nano(row["reserved_nano"]),
        status=row["status"],
    )


def _settlement_from_row(row: sqlite3.Row) -> BudgetSettlement:
    return BudgetSettlement(
        call_id=row["call_id"],
        pricing=_pricing_from_row(row),
        maximum_usage=ModelUsage.model_validate_json(row["maximum_usage_json"]),
        actual_usage=ModelUsage.model_validate_json(row["actual_usage_json"]),
        reserved_cost_usd=_from_nano(row["reserved_nano"]),
        actual_cost_usd=_from_nano(row["actual_nano"]),
    )


def _to_nano(value: Decimal) -> int:
    return int((value * _NANODOLLARS).to_integral_value(rounding=ROUND_CEILING))


def _from_nano(value: int) -> Decimal:
    return (Decimal(value) / _NANODOLLARS).quantize(_NINE_PLACES)
