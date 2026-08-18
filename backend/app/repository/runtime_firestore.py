from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from typing import Any, Protocol, TypeVar

from google.cloud import firestore
from pydantic import BaseModel

from app.repository.runtime_validation import (
    build_committed_snapshot,
    validate_initial_snapshot,
)
from app.runtime.entities import InboxRecord, OutboxMessage, RuntimeSnapshot
from app.runtime.errors import RuntimeDomainError
from app.runtime.mutations import RuntimeMutation


Result = TypeVar("Result")


class TransactionRunner(Protocol):
    def __call__(self, callback: Callable[[Any], Result]) -> Result: ...


class FirestoreRuntimeRepository:
    """Firestore-backed Mission aggregate with transactional query projections.

    The mission document is the recovery boundary and stores the complete validated
    aggregate. Canonical entities are projected into subcollections in the same
    transaction so Mission Control and operational tools can query them directly.
    """

    store_kind = "firestore"

    def __init__(
        self,
        client: Any,
        *,
        collection: str = "missions",
        transaction_runner: TransactionRunner | None = None,
    ) -> None:
        self._client = client
        self._missions = client.collection(collection)
        self._transaction_runner = transaction_runner or self._run_transaction

    @classmethod
    def from_environment(
        cls,
        *,
        project: str | None = None,
        database: str | None = None,
        collection: str = "missions",
    ) -> "FirestoreRuntimeRepository":
        options: dict[str, str] = {}
        if project:
            options["project"] = project
        if database:
            options["database"] = database
        return cls(firestore.Client(**options), collection=collection)

    def create(self, snapshot: RuntimeSnapshot) -> None:
        validate_initial_snapshot(snapshot)
        mission_id = snapshot.mission.mission_id
        reference = self._missions.document(mission_id)

        def create_in_transaction(transaction: Any) -> None:
            existing = _transaction_get(transaction, reference)
            if existing.exists:
                raise RuntimeDomainError(
                    "MISSION_ALREADY_EXISTS",
                    f"mission already exists: {mission_id}",
                )
            transaction.create(reference, _mission_document(snapshot))
            _write_full_projection(transaction, reference, snapshot)

        self._transaction_runner(create_in_transaction)

    def load(self, mission_id: str) -> RuntimeSnapshot:
        reference = self._missions.document(mission_id)

        def load_in_transaction(transaction: Any) -> RuntimeSnapshot:
            return _snapshot_from_document(
                mission_id,
                _transaction_get(transaction, reference),
            )

        return self._transaction_runner(load_in_transaction).model_copy(deep=True)

    def find_inbox(
        self,
        mission_id: str,
        message_id: str,
    ) -> InboxRecord | None:
        snapshot = self.load(mission_id)
        for record in snapshot.inbox:
            if record.message_id == message_id:
                return record.model_copy(deep=True)
        return None

    def commit(
        self,
        mission_id: str,
        expected_revision: int,
        mutation: RuntimeMutation,
    ) -> RuntimeSnapshot:
        reference = self._missions.document(mission_id)

        def commit_in_transaction(transaction: Any) -> RuntimeSnapshot:
            current = _snapshot_from_document(
                mission_id,
                _transaction_get(transaction, reference),
            )
            committed = build_committed_snapshot(
                current,
                expected_revision,
                mutation,
            )
            transaction.set(reference, _mission_document(committed))
            _write_mutation_projection(
                transaction,
                reference,
                committed,
                mutation,
            )
            return committed

        return self._transaction_runner(commit_in_transaction).model_copy(deep=True)

    def mark_outbox_published(
        self,
        mission_id: str,
        outbox_message_id: str,
        published_at: datetime,
    ) -> OutboxMessage:
        reference = self._missions.document(mission_id)

        def mark_in_transaction(transaction: Any) -> OutboxMessage:
            snapshot = _snapshot_from_document(
                mission_id,
                _transaction_get(transaction, reference),
            )
            for index, message in enumerate(snapshot.outbox):
                if message.outbox_message_id != outbox_message_id:
                    continue
                if message.published_at is None:
                    message = message.model_copy(
                        update={"published_at": published_at},
                        deep=True,
                    )
                    snapshot.outbox[index] = message
                    transaction.set(reference, _mission_document(snapshot))
                    _set_models(
                        transaction,
                        reference,
                        "outbox",
                        [message],
                        "outbox_message_id",
                    )
                return message
            raise RuntimeDomainError(
                "OUTBOX_MESSAGE_NOT_FOUND",
                f"outbox message does not exist: {outbox_message_id}",
            )

        return self._transaction_runner(mark_in_transaction).model_copy(deep=True)

    def _run_transaction(self, callback: Callable[[Any], Result]) -> Result:
        transaction = self._client.transaction()

        @firestore.transactional
        def execute(active_transaction: Any) -> Result:
            return callback(active_transaction)

        return execute(transaction)


def _transaction_get(transaction: Any, reference: Any) -> Any:
    result = transaction.get(reference)
    if hasattr(result, "exists"):
        return result
    return next(iter(result))


def _snapshot_from_document(mission_id: str, document: Any) -> RuntimeSnapshot:
    if not document.exists:
        raise RuntimeDomainError(
            "MISSION_NOT_FOUND",
            f"mission does not exist: {mission_id}",
        )
    data = document.to_dict() or {}
    payload = data.get("snapshot_json")
    if not isinstance(payload, str):
        raise RuntimeDomainError(
            "PERSISTENCE_CORRUPT",
            f"mission snapshot is missing: {mission_id}",
        )
    return RuntimeSnapshot.model_validate_json(payload)


def _mission_document(snapshot: RuntimeSnapshot) -> dict[str, Any]:
    mission = snapshot.mission
    return {
        "mission_id": mission.mission_id,
        "mission_type": mission.mission_type,
        "subject_id": mission.subject_id,
        "status": mission.status.value,
        "revision": mission.revision,
        "event_sequence": mission.event_sequence,
        "created_at": mission.created_at,
        "updated_at": mission.updated_at,
        "unpublished_outbox_count": sum(
            message.published_at is None for message in snapshot.outbox
        ),
        "schema_version": 1,
        "snapshot_json": snapshot.model_dump_json(),
    }


def _write_full_projection(
    transaction: Any,
    mission_reference: Any,
    snapshot: RuntimeSnapshot,
) -> None:
    _set_models(transaction, mission_reference, "work_items", snapshot.work_items, "work_item_id")
    _set_models(
        transaction,
        mission_reference,
        "commitments",
        snapshot.commitments,
        "commitment_id",
    )
    _set_models(
        transaction,
        mission_reference,
        "side_effects",
        snapshot.side_effects,
        "side_effect_id",
    )
    _set_models(transaction, mission_reference, "inbox", snapshot.inbox, "message_id")
    _set_models(
        transaction,
        mission_reference,
        "outbox",
        snapshot.outbox,
        "outbox_message_id",
    )
    _set_models(
        transaction,
        mission_reference,
        "domain_events",
        snapshot.audit_events,
        "audit_event_id",
    )
    _write_world_projection(transaction, mission_reference, snapshot)
    _write_graph_projection(transaction, mission_reference, snapshot)


def _write_mutation_projection(
    transaction: Any,
    mission_reference: Any,
    committed: RuntimeSnapshot,
    mutation: RuntimeMutation,
) -> None:
    _set_models(transaction, mission_reference, "work_items", mutation.work_upserts, "work_item_id")
    _set_models(
        transaction,
        mission_reference,
        "commitments",
        mutation.commitment_upserts,
        "commitment_id",
    )
    _set_models(
        transaction,
        mission_reference,
        "side_effects",
        mutation.side_effect_upserts,
        "side_effect_id",
    )
    _set_models(
        transaction,
        mission_reference,
        "inbox",
        [mutation.inbox_completion],
        "message_id",
    )
    _set_models(
        transaction,
        mission_reference,
        "outbox",
        mutation.outbox_appends,
        "outbox_message_id",
    )
    _set_models(
        transaction,
        mission_reference,
        "domain_events",
        mutation.audit_appends,
        "audit_event_id",
    )
    if mutation.world is not None:
        _write_world_projection(transaction, mission_reference, committed)
    if mutation.graph is not None:
        _write_graph_projection(transaction, mission_reference, committed)


def _write_world_projection(
    transaction: Any,
    mission_reference: Any,
    snapshot: RuntimeSnapshot,
) -> None:
    if snapshot.world is None:
        return
    world = snapshot.world
    transaction.set(
        mission_reference.collection("world").document("current"),
        world.model_dump(mode="python"),
    )
    _set_models(
        transaction,
        mission_reference,
        "world_artifacts",
        world.artifacts.values(),
        "artifact_id",
    )


def _write_graph_projection(
    transaction: Any,
    mission_reference: Any,
    snapshot: RuntimeSnapshot,
) -> None:
    graph = snapshot.graph
    _set_models(transaction, mission_reference, "artifacts", graph.artifacts.values(), "artifact_id")
    _set_models(transaction, mission_reference, "evidence", graph.evidences.values(), "evidence_id")
    _set_models(transaction, mission_reference, "decisions", graph.decisions.values(), "decision_id")
    _set_models(transaction, mission_reference, "actions", graph.actions.values(), "action_id")
    _set_models(transaction, mission_reference, "dependency_edges", graph.edges, "edge_id")
    _set_models(transaction, mission_reference, "graph_events", graph.events, "event_id")
    _set_models(transaction, mission_reference, "dispatches", graph.dispatches, "dispatch_id")
    transaction.set(
        mission_reference.collection("graph_state").document("current"),
        {
            "cause_by_node_id": graph.cause_by_node_id,
            "metadata": graph.metadata,
        },
    )


def _set_models(
    transaction: Any,
    mission_reference: Any,
    collection: str,
    models: Any,
    identity_field: str,
) -> None:
    for model in models:
        if not isinstance(model, BaseModel):
            raise TypeError(f"projection requires Pydantic models, found {type(model)!r}")
        document_id = str(getattr(model, identity_field))
        transaction.set(
            mission_reference.collection(collection).document(document_id),
            model.model_dump(mode="python"),
        )
