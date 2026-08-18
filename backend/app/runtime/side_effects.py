from typing import Any

from app.domain.models import DecisionStatus
from app.runtime.entities import (
    SideEffectRecord,
    SideEffectStatus,
    utc_now,
)
from app.runtime.errors import RuntimeDomainError


class SideEffectLedger:
    @staticmethod
    def intent(
        *,
        side_effect_id: str,
        mission_id: str,
        effect_type: str,
        idempotency_key: str,
        authorization_decision_id: str,
        request: dict[str, Any],
    ) -> SideEffectRecord:
        return SideEffectRecord(
            side_effect_id=side_effect_id,
            mission_id=mission_id,
            effect_type=effect_type,
            idempotency_key=idempotency_key,
            authorization_decision_id=authorization_decision_id,
            request=request,
        )

    @staticmethod
    def begin(
        effect: SideEffectRecord,
        authorization: DecisionStatus,
    ) -> SideEffectRecord:
        if effect.status is SideEffectStatus.COMMITTED:
            return effect.model_copy(deep=True)
        if authorization is not DecisionStatus.VALID:
            raise RuntimeDomainError(
                "STALE_AUTHORIZATION",
                "only a VALID decision may authorize a side effect",
            )
        if effect.status is SideEffectStatus.RECONCILIATION_REQUIRED:
            raise RuntimeDomainError(
                "SIDE_EFFECT_RECONCILIATION_REQUIRED",
                "reconcile the external result before retry",
            )
        if effect.status not in {
            SideEffectStatus.INTENDED,
            SideEffectStatus.FAILED_RETRYABLE,
        }:
            raise RuntimeDomainError(
                "INVALID_SIDE_EFFECT_TRANSITION",
                f"cannot begin side effect from {effect.status}",
            )
        return SideEffectLedger._updated(
            effect,
            status=SideEffectStatus.EXECUTING,
        )

    @staticmethod
    def commit(
        effect: SideEffectRecord,
        *,
        result: dict[str, Any],
    ) -> SideEffectRecord:
        SideEffectLedger._require_status(effect, SideEffectStatus.EXECUTING)
        return SideEffectLedger._updated(
            effect,
            status=SideEffectStatus.COMMITTED,
            result=result,
        )

    @staticmethod
    def record_unknown(effect: SideEffectRecord) -> SideEffectRecord:
        SideEffectLedger._require_status(effect, SideEffectStatus.EXECUTING)
        return SideEffectLedger._updated(
            effect,
            status=SideEffectStatus.RECONCILIATION_REQUIRED,
        )

    @staticmethod
    def record_failure(
        effect: SideEffectRecord,
        *,
        retryable: bool,
        result: dict[str, Any],
    ) -> SideEffectRecord:
        SideEffectLedger._require_status(effect, SideEffectStatus.EXECUTING)
        return SideEffectLedger._updated(
            effect,
            status=(
                SideEffectStatus.FAILED_RETRYABLE
                if retryable
                else SideEffectStatus.FAILED_FINAL
            ),
            result=result,
        )

    @staticmethod
    def reconcile(
        effect: SideEffectRecord,
        *,
        externally_committed: bool,
        result: dict[str, Any],
    ) -> SideEffectRecord:
        SideEffectLedger._require_status(
            effect,
            SideEffectStatus.RECONCILIATION_REQUIRED,
        )
        return SideEffectLedger._updated(
            effect,
            status=(
                SideEffectStatus.COMMITTED
                if externally_committed
                else SideEffectStatus.FAILED_RETRYABLE
            ),
            result=result,
        )

    @staticmethod
    def _require_status(
        effect: SideEffectRecord,
        expected: SideEffectStatus,
    ) -> None:
        if effect.status is not expected:
            raise RuntimeDomainError(
                "INVALID_SIDE_EFFECT_TRANSITION",
                f"expected {expected}, found {effect.status}",
            )

    @staticmethod
    def _updated(
        effect: SideEffectRecord,
        *,
        status: SideEffectStatus,
        result: dict[str, Any] | None = None,
    ) -> SideEffectRecord:
        changes: dict[str, Any] = {
            "status": status,
            "updated_at": utc_now(),
        }
        if result is not None:
            changes["result"] = result
        return effect.model_copy(update=changes, deep=True)
