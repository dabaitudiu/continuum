import pytest

from app.domain.models import DecisionStatus
from app.runtime.entities import SideEffectRecord, SideEffectStatus
from app.runtime.errors import RuntimeDomainError
from app.runtime.side_effects import SideEffectLedger


def intended_effect() -> SideEffectRecord:
    return SideEffectLedger.intent(
        side_effect_id="effect:activate-acme",
        mission_id="m-1",
        effect_type="ACTIVATE_VENDOR",
        idempotency_key="activate:ACME",
        authorization_decision_id="D50",
        request={"vendor_id": "ACME"},
    )


def executing_effect() -> SideEffectRecord:
    return SideEffectLedger.begin(intended_effect(), DecisionStatus.VALID)


def test_intent_records_stable_authorization_and_idempotency_identity() -> None:
    effect = intended_effect()

    assert effect.status is SideEffectStatus.INTENDED
    assert effect.idempotency_key == "activate:ACME"
    assert effect.authorization_decision_id == "D50"
    assert effect.request == {"vendor_id": "ACME"}


@pytest.mark.parametrize(
    "unauthorized",
    [
        DecisionStatus.STALE,
        DecisionStatus.REVALIDATING,
        DecisionStatus.INVALID,
        DecisionStatus.SUPERSEDED,
    ],
)
def test_nonvalid_decision_cannot_authorize_side_effect(
    unauthorized: DecisionStatus,
) -> None:
    with pytest.raises(RuntimeDomainError) as raised:
        SideEffectLedger.begin(intended_effect(), unauthorized)

    assert raised.value.code == "STALE_AUTHORIZATION"


def test_valid_decision_begins_side_effect_without_mutating_intent() -> None:
    intent = intended_effect()

    executing = SideEffectLedger.begin(intent, DecisionStatus.VALID)

    assert executing.status is SideEffectStatus.EXECUTING
    assert intent.status is SideEffectStatus.INTENDED
    assert executing.updated_at >= intent.updated_at


def test_committed_effect_is_idempotent() -> None:
    committed = SideEffectLedger.commit(
        executing_effect(),
        result={"vendor_status": "ACTIVE"},
    )

    replay = SideEffectLedger.begin(committed, DecisionStatus.VALID)

    assert replay == committed
    assert replay.result == {"vendor_status": "ACTIVE"}


def test_unknown_result_requires_reconciliation_before_retry() -> None:
    unknown = SideEffectLedger.record_unknown(executing_effect())

    assert unknown.status is SideEffectStatus.RECONCILIATION_REQUIRED
    with pytest.raises(RuntimeDomainError) as raised:
        SideEffectLedger.begin(unknown, DecisionStatus.VALID)

    assert raised.value.code == "SIDE_EFFECT_RECONCILIATION_REQUIRED"


@pytest.mark.parametrize(
    ("externally_committed", "expected"),
    [
        (True, SideEffectStatus.COMMITTED),
        (False, SideEffectStatus.FAILED_RETRYABLE),
    ],
)
def test_reconciliation_records_observed_external_state(
    externally_committed: bool,
    expected: SideEffectStatus,
) -> None:
    unknown = SideEffectLedger.record_unknown(executing_effect())

    reconciled = SideEffectLedger.reconcile(
        unknown,
        externally_committed=externally_committed,
        result={"observed": externally_committed},
    )

    assert reconciled.status is expected
    assert reconciled.result == {"observed": externally_committed}


def test_retryable_failure_can_begin_again_with_valid_authorization() -> None:
    failed = SideEffectLedger.record_failure(
        executing_effect(),
        retryable=True,
        result={"code": "TIMEOUT"},
    )

    retry = SideEffectLedger.begin(failed, DecisionStatus.VALID)

    assert retry.status is SideEffectStatus.EXECUTING


def test_final_failure_cannot_retry() -> None:
    failed = SideEffectLedger.record_failure(
        executing_effect(),
        retryable=False,
        result={"code": "REJECTED"},
    )

    with pytest.raises(RuntimeDomainError) as raised:
        SideEffectLedger.begin(failed, DecisionStatus.VALID)

    assert raised.value.code == "INVALID_SIDE_EFFECT_TRANSITION"


@pytest.mark.parametrize(
    ("operation", "start_status"),
    [
        (lambda effect: SideEffectLedger.commit(effect, result={}), SideEffectStatus.INTENDED),
        (lambda effect: SideEffectLedger.record_unknown(effect), SideEffectStatus.INTENDED),
        (
            lambda effect: SideEffectLedger.reconcile(
                effect,
                externally_committed=True,
                result={},
            ),
            SideEffectStatus.EXECUTING,
        ),
    ],
)
def test_ledger_rejects_illegal_transitions(operation, start_status) -> None:  # type: ignore[no-untyped-def]
    effect = intended_effect().model_copy(update={"status": start_status})

    with pytest.raises(RuntimeDomainError) as raised:
        operation(effect)

    assert raised.value.code == "INVALID_SIDE_EFFECT_TRANSITION"
