from collections.abc import Callable
from typing import TypeVar

from pydantic import BaseModel

from app.runtime.entities import RuntimeSnapshot, SideEffectRecord, utc_now
from app.runtime.errors import RuntimeDomainError
from app.runtime.mutations import RuntimeMutation


Entity = TypeVar("Entity", bound=BaseModel)


def build_committed_snapshot(
    current: RuntimeSnapshot,
    expected_revision: int,
    mutation: RuntimeMutation,
) -> RuntimeSnapshot:
    mission_id = current.mission.mission_id
    if current.mission.revision != expected_revision:
        raise RuntimeDomainError(
            "REVISION_CONFLICT",
            f"expected revision {expected_revision}, found {current.mission.revision}",
        )
    _require_mission(mutation.mission.mission_id, mission_id)
    _require_mission(mutation.inbox_completion.mission_id, mission_id)
    if any(
        record.message_id == mutation.inbox_completion.message_id
        for record in current.inbox
    ):
        raise RuntimeDomainError(
            "MESSAGE_ALREADY_PROCESSED",
            f"message already processed: {mutation.inbox_completion.message_id}",
        )
    _validate_audit(current, mutation)
    _validate_entity_missions(mission_id, mutation)
    _validate_outbox(current, mutation)

    result = current.model_copy(deep=True)
    result.mission = mutation.mission.model_copy(
        update={
            "revision": expected_revision + 1,
            "event_sequence": mutation.audit_appends[-1].event_sequence,
            "updated_at": utc_now(),
        },
        deep=True,
    )
    result.work_items = _upsert(
        result.work_items,
        mutation.work_upserts,
        lambda item: item.work_item_id,
    )
    result.commitments = _upsert(
        result.commitments,
        mutation.commitment_upserts,
        lambda item: item.commitment_id,
    )
    result.side_effects = _upsert(
        result.side_effects,
        mutation.side_effect_upserts,
        lambda item: item.side_effect_id,
    )
    _validate_side_effect_idempotency(result.side_effects)
    if mutation.world is not None:
        _require_mission(mutation.world.mission_id, mission_id)
        result.world = mutation.world.model_copy(deep=True)
    if mutation.graph is not None:
        _require_mission(mutation.graph.mission_id, mission_id)
        result.graph = mutation.graph.model_copy(deep=True)
    result.audit_events.extend(
        event.model_copy(deep=True) for event in mutation.audit_appends
    )
    result.inbox.append(mutation.inbox_completion.model_copy(deep=True))
    result.outbox.extend(
        message.model_copy(deep=True) for message in mutation.outbox_appends
    )
    return result


def validate_initial_snapshot(snapshot: RuntimeSnapshot) -> None:
    mission_id = snapshot.mission.mission_id
    _require_mission(snapshot.graph.mission_id, mission_id)
    if snapshot.world is not None:
        _require_mission(snapshot.world.mission_id, mission_id)
    for entity in (
        *snapshot.work_items,
        *snapshot.commitments,
        *snapshot.side_effects,
        *snapshot.inbox,
        *snapshot.outbox,
        *snapshot.audit_events,
    ):
        _require_mission(entity.mission_id, mission_id)
    _validate_side_effect_idempotency(snapshot.side_effects)
    outbox_ids = [message.outbox_message_id for message in snapshot.outbox]
    if len(outbox_ids) != len(set(outbox_ids)):
        raise RuntimeDomainError(
            "OUTBOX_MESSAGE_CONFLICT",
            "outbox message ids must be unique",
        )
    expected_sequences = list(range(1, len(snapshot.audit_events) + 1))
    actual_sequences = [event.event_sequence for event in snapshot.audit_events]
    if actual_sequences != expected_sequences:
        raise RuntimeDomainError(
            "AUDIT_SEQUENCE_CONFLICT",
            "initial audit sequence must be contiguous from 1",
        )
    if snapshot.mission.event_sequence != len(snapshot.audit_events):
        raise RuntimeDomainError(
            "AUDIT_SEQUENCE_CONFLICT",
            "mission event sequence does not match audit history",
        )


def _validate_audit(
    current: RuntimeSnapshot,
    mutation: RuntimeMutation,
) -> None:
    if not mutation.audit_appends:
        raise RuntimeDomainError(
            "AUDIT_SEQUENCE_CONFLICT",
            "a runtime mutation must append at least one audit event",
        )
    first = current.mission.event_sequence + 1
    expected = list(range(first, first + len(mutation.audit_appends)))
    actual = [event.event_sequence for event in mutation.audit_appends]
    if actual != expected:
        raise RuntimeDomainError(
            "AUDIT_SEQUENCE_CONFLICT",
            f"expected audit sequences {expected}, found {actual}",
        )
    existing_ids = {event.audit_event_id for event in current.audit_events}
    new_ids = [event.audit_event_id for event in mutation.audit_appends]
    if len(new_ids) != len(set(new_ids)) or existing_ids.intersection(new_ids):
        raise RuntimeDomainError(
            "AUDIT_EVENT_CONFLICT",
            "audit event ids must be unique",
        )


def _validate_entity_missions(
    mission_id: str,
    mutation: RuntimeMutation,
) -> None:
    if mutation.world is not None:
        _require_mission(mutation.world.mission_id, mission_id)
    for entity in (
        *mutation.work_upserts,
        *mutation.commitment_upserts,
        *mutation.side_effect_upserts,
        *mutation.audit_appends,
        *mutation.outbox_appends,
    ):
        _require_mission(entity.mission_id, mission_id)


def _validate_outbox(
    current: RuntimeSnapshot,
    mutation: RuntimeMutation,
) -> None:
    existing_ids = {message.outbox_message_id for message in current.outbox}
    new_ids = [message.outbox_message_id for message in mutation.outbox_appends]
    if len(new_ids) != len(set(new_ids)) or existing_ids.intersection(new_ids):
        raise RuntimeDomainError(
            "OUTBOX_MESSAGE_CONFLICT",
            "outbox message ids must be unique",
        )


def _require_mission(actual: str, expected: str) -> None:
    if actual != expected:
        raise RuntimeDomainError(
            "MISSION_ID_CONFLICT",
            f"expected mission {expected}, found {actual}",
        )


def _validate_side_effect_idempotency(
    side_effects: list[SideEffectRecord],
) -> None:
    owner_by_key: dict[str, str] = {}
    for effect in side_effects:
        owner = owner_by_key.setdefault(
            effect.idempotency_key,
            effect.side_effect_id,
        )
        if owner != effect.side_effect_id:
            raise RuntimeDomainError(
                "SIDE_EFFECT_IDEMPOTENCY_CONFLICT",
                f"idempotency key already belongs to {owner}",
            )


def _upsert(
    existing: list[Entity],
    changes: list[Entity],
    identity: Callable[[Entity], str],
) -> list[Entity]:
    by_id = {identity(item): item.model_copy(deep=True) for item in existing}
    for item in changes:
        by_id[identity(item)] = item.model_copy(deep=True)
    return list(by_id.values())
