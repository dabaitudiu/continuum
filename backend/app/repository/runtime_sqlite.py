from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from threading import RLock

from app.domain.models import (
    ActionNode,
    DecisionNode,
    DependencyEdge,
    DispatchRecord,
    DomainEvent,
    EvidenceNode,
    GraphSnapshot,
    WorldArtifact,
)
from app.repository.runtime_validation import (
    build_committed_snapshot,
    validate_initial_snapshot,
)
from app.runtime.entities import (
    AuditEvent,
    Commitment,
    EnterpriseWorld,
    InboxRecord,
    Mission,
    OutboxMessage,
    RuntimeSnapshot,
    SideEffectRecord,
    WorkItem,
)
from app.runtime.errors import RuntimeDomainError
from app.runtime.mutations import RuntimeMutation


SCHEMA = """
CREATE TABLE IF NOT EXISTS missions (
    mission_id TEXT PRIMARY KEY,
    status TEXT NOT NULL,
    revision INTEGER NOT NULL,
    event_sequence INTEGER NOT NULL,
    payload TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS work_items (
    mission_id TEXT NOT NULL,
    work_item_id TEXT NOT NULL,
    status TEXT NOT NULL,
    work_type TEXT NOT NULL,
    position INTEGER NOT NULL,
    payload TEXT NOT NULL,
    PRIMARY KEY (mission_id, work_item_id),
    FOREIGN KEY (mission_id) REFERENCES missions(mission_id) ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS commitments (
    mission_id TEXT NOT NULL,
    commitment_id TEXT NOT NULL,
    status TEXT NOT NULL,
    event_type TEXT NOT NULL,
    position INTEGER NOT NULL,
    payload TEXT NOT NULL,
    PRIMARY KEY (mission_id, commitment_id),
    FOREIGN KEY (mission_id) REFERENCES missions(mission_id) ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS side_effects (
    mission_id TEXT NOT NULL,
    side_effect_id TEXT NOT NULL,
    idempotency_key TEXT NOT NULL,
    status TEXT NOT NULL,
    position INTEGER NOT NULL,
    payload TEXT NOT NULL,
    PRIMARY KEY (mission_id, side_effect_id),
    UNIQUE (mission_id, idempotency_key),
    FOREIGN KEY (mission_id) REFERENCES missions(mission_id) ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS inbox_messages (
    mission_id TEXT NOT NULL,
    message_id TEXT NOT NULL,
    message_type TEXT NOT NULL,
    position INTEGER NOT NULL,
    payload TEXT NOT NULL,
    PRIMARY KEY (mission_id, message_id),
    FOREIGN KEY (mission_id) REFERENCES missions(mission_id) ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS outbox_messages (
    mission_id TEXT NOT NULL,
    outbox_message_id TEXT NOT NULL,
    event_type TEXT NOT NULL,
    position INTEGER NOT NULL,
    payload TEXT NOT NULL,
    PRIMARY KEY (mission_id, outbox_message_id),
    FOREIGN KEY (mission_id) REFERENCES missions(mission_id) ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS audit_events (
    mission_id TEXT NOT NULL,
    audit_event_id TEXT NOT NULL,
    event_sequence INTEGER NOT NULL,
    event_type TEXT NOT NULL,
    payload TEXT NOT NULL,
    PRIMARY KEY (mission_id, event_sequence),
    UNIQUE (mission_id, audit_event_id),
    FOREIGN KEY (mission_id) REFERENCES missions(mission_id) ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS graph_state (
    mission_id TEXT PRIMARY KEY,
    cause_by_node_id TEXT NOT NULL,
    metadata TEXT NOT NULL,
    FOREIGN KEY (mission_id) REFERENCES missions(mission_id) ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS simulator_world (
    mission_id TEXT PRIMARY KEY,
    current_policy_id TEXT NOT NULL,
    vendor_status TEXT NOT NULL,
    payload TEXT NOT NULL,
    FOREIGN KEY (mission_id) REFERENCES missions(mission_id) ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS world_artifacts (
    mission_id TEXT NOT NULL,
    artifact_id TEXT NOT NULL,
    logical_key TEXT NOT NULL,
    status TEXT NOT NULL,
    payload TEXT NOT NULL,
    PRIMARY KEY (mission_id, artifact_id),
    FOREIGN KEY (mission_id) REFERENCES missions(mission_id) ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS evidence_nodes (
    mission_id TEXT NOT NULL,
    evidence_id TEXT NOT NULL,
    kind TEXT NOT NULL,
    status TEXT NOT NULL,
    payload TEXT NOT NULL,
    PRIMARY KEY (mission_id, evidence_id),
    FOREIGN KEY (mission_id) REFERENCES missions(mission_id) ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS decisions (
    mission_id TEXT NOT NULL,
    decision_id TEXT NOT NULL,
    decision_type TEXT NOT NULL,
    status TEXT NOT NULL,
    payload TEXT NOT NULL,
    PRIMARY KEY (mission_id, decision_id),
    FOREIGN KEY (mission_id) REFERENCES missions(mission_id) ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS actions (
    mission_id TEXT NOT NULL,
    action_id TEXT NOT NULL,
    action_type TEXT NOT NULL,
    status TEXT NOT NULL,
    payload TEXT NOT NULL,
    PRIMARY KEY (mission_id, action_id),
    FOREIGN KEY (mission_id) REFERENCES missions(mission_id) ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS dependency_edges (
    mission_id TEXT NOT NULL,
    edge_id TEXT NOT NULL,
    position INTEGER NOT NULL,
    payload TEXT NOT NULL,
    PRIMARY KEY (mission_id, edge_id),
    FOREIGN KEY (mission_id) REFERENCES missions(mission_id) ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS graph_events (
    mission_id TEXT NOT NULL,
    event_id TEXT NOT NULL,
    position INTEGER NOT NULL,
    payload TEXT NOT NULL,
    PRIMARY KEY (mission_id, event_id),
    FOREIGN KEY (mission_id) REFERENCES missions(mission_id) ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS dispatch_records (
    mission_id TEXT NOT NULL,
    dispatch_id TEXT NOT NULL,
    position INTEGER NOT NULL,
    payload TEXT NOT NULL,
    PRIMARY KEY (mission_id, dispatch_id),
    FOREIGN KEY (mission_id) REFERENCES missions(mission_id) ON DELETE CASCADE
);
"""


CHILD_TABLES = (
    "work_items",
    "commitments",
    "side_effects",
    "inbox_messages",
    "outbox_messages",
    "audit_events",
    "graph_state",
    "simulator_world",
    "world_artifacts",
    "evidence_nodes",
    "decisions",
    "actions",
    "dependency_edges",
    "graph_events",
    "dispatch_records",
)


class SQLiteRuntimeRepository:
    store_kind = "sqlite"

    def __init__(self, path: Path) -> None:
        self._path = Path(path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._connection = sqlite3.connect(
            self._path,
            isolation_level=None,
            check_same_thread=False,
        )
        self._connection.row_factory = sqlite3.Row
        self._connection.execute("PRAGMA foreign_keys = ON")
        self._connection.executescript(SCHEMA)
        self._lock = RLock()

    def close(self) -> None:
        with self._lock:
            self._connection.close()

    def create(self, snapshot: RuntimeSnapshot) -> None:
        with self._lock:
            validate_initial_snapshot(snapshot)
            self._connection.execute("BEGIN IMMEDIATE")
            try:
                if self._mission_exists(snapshot.mission.mission_id):
                    raise RuntimeDomainError(
                        "MISSION_ALREADY_EXISTS",
                        f"mission already exists: {snapshot.mission.mission_id}",
                    )
                self._insert_mission(snapshot.mission)
                self._write_children(snapshot)
                self._connection.execute("COMMIT")
            except Exception:
                self._connection.execute("ROLLBACK")
                raise

    def load(self, mission_id: str) -> RuntimeSnapshot:
        with self._lock:
            return self._load_locked(mission_id)

    def find_inbox(
        self,
        mission_id: str,
        message_id: str,
    ) -> InboxRecord | None:
        with self._lock:
            if not self._mission_exists(mission_id):
                raise RuntimeDomainError(
                    "MISSION_NOT_FOUND",
                    f"mission does not exist: {mission_id}",
                )
            row = self._connection.execute(
                "SELECT payload FROM inbox_messages WHERE mission_id = ? AND message_id = ?",
                (mission_id, message_id),
            ).fetchone()
            return None if row is None else InboxRecord.model_validate_json(row[0])

    def commit(
        self,
        mission_id: str,
        expected_revision: int,
        mutation: RuntimeMutation,
    ) -> RuntimeSnapshot:
        with self._lock:
            self._connection.execute("BEGIN IMMEDIATE")
            try:
                current = self._load_locked(mission_id)
                committed = build_committed_snapshot(
                    current,
                    expected_revision,
                    mutation,
                )
                updated = self._connection.execute(
                    """
                    UPDATE missions
                    SET status = ?, revision = ?, event_sequence = ?, payload = ?
                    WHERE mission_id = ? AND revision = ?
                    """,
                    (
                        committed.mission.status.value,
                        committed.mission.revision,
                        committed.mission.event_sequence,
                        committed.mission.model_dump_json(),
                        mission_id,
                        expected_revision,
                    ),
                )
                if updated.rowcount != 1:
                    raise RuntimeDomainError(
                        "REVISION_CONFLICT",
                        f"revision changed while committing mission {mission_id}",
                    )
                self._delete_children(mission_id)
                self._write_children(committed)
                self._connection.execute("COMMIT")
                return committed.model_copy(deep=True)
            except sqlite3.IntegrityError as error:
                self._connection.execute("ROLLBACK")
                raise RuntimeDomainError(
                    "PERSISTENCE_CONFLICT",
                    str(error),
                ) from error
            except Exception:
                self._connection.execute("ROLLBACK")
                raise

    def mark_outbox_published(
        self,
        mission_id: str,
        outbox_message_id: str,
        published_at: datetime,
    ) -> OutboxMessage:
        with self._lock:
            if not self._mission_exists(mission_id):
                raise RuntimeDomainError(
                    "MISSION_NOT_FOUND",
                    f"mission does not exist: {mission_id}",
                )
            row = self._connection.execute(
                """
                SELECT payload FROM outbox_messages
                WHERE mission_id = ? AND outbox_message_id = ?
                """,
                (mission_id, outbox_message_id),
            ).fetchone()
            if row is None:
                raise RuntimeDomainError(
                    "OUTBOX_MESSAGE_NOT_FOUND",
                    f"outbox message does not exist: {outbox_message_id}",
                )
            message = OutboxMessage.model_validate_json(row[0])
            if message.published_at is not None:
                return message
            published = message.model_copy(
                update={"published_at": published_at},
                deep=True,
            )
            self._connection.execute(
                """
                UPDATE outbox_messages SET payload = ?
                WHERE mission_id = ? AND outbox_message_id = ?
                """,
                (published.model_dump_json(), mission_id, outbox_message_id),
            )
            return published

    def _load_locked(self, mission_id: str) -> RuntimeSnapshot:
        mission_row = self._connection.execute(
            "SELECT payload FROM missions WHERE mission_id = ?",
            (mission_id,),
        ).fetchone()
        if mission_row is None:
            raise RuntimeDomainError(
                "MISSION_NOT_FOUND",
                f"mission does not exist: {mission_id}",
            )

        state_row = self._connection.execute(
            "SELECT cause_by_node_id, metadata FROM graph_state WHERE mission_id = ?",
            (mission_id,),
        ).fetchone()
        cause_by_node_id = {} if state_row is None else json.loads(state_row[0])
        metadata = {} if state_row is None else json.loads(state_row[1])
        graph = GraphSnapshot(
            mission_id=mission_id,
            artifacts=self._load_dict(
                "world_artifacts",
                "artifact_id",
                mission_id,
                WorldArtifact,
            ),
            evidences=self._load_dict(
                "evidence_nodes",
                "evidence_id",
                mission_id,
                EvidenceNode,
            ),
            decisions=self._load_dict(
                "decisions",
                "decision_id",
                mission_id,
                DecisionNode,
            ),
            actions=self._load_dict(
                "actions",
                "action_id",
                mission_id,
                ActionNode,
            ),
            edges=self._load_list(
                "dependency_edges",
                mission_id,
                DependencyEdge,
            ),
            events=self._load_list("graph_events", mission_id, DomainEvent),
            dispatches=self._load_list(
                "dispatch_records",
                mission_id,
                DispatchRecord,
            ),
            cause_by_node_id=cause_by_node_id,
            metadata=metadata,
        )
        return RuntimeSnapshot(
            mission=Mission.model_validate_json(mission_row[0]),
            graph=graph,
            world=self._load_world(mission_id),
            work_items=self._load_list("work_items", mission_id, WorkItem),
            commitments=self._load_list(
                "commitments",
                mission_id,
                Commitment,
            ),
            side_effects=self._load_list(
                "side_effects",
                mission_id,
                SideEffectRecord,
            ),
            inbox=self._load_list("inbox_messages", mission_id, InboxRecord),
            outbox=self._load_list(
                "outbox_messages",
                mission_id,
                OutboxMessage,
            ),
            audit_events=self._load_audit(mission_id),
        )

    def _mission_exists(self, mission_id: str) -> bool:
        return (
            self._connection.execute(
                "SELECT 1 FROM missions WHERE mission_id = ?",
                (mission_id,),
            ).fetchone()
            is not None
        )

    def _insert_mission(self, mission: Mission) -> None:
        self._connection.execute(
            "INSERT INTO missions VALUES (?, ?, ?, ?, ?)",
            (
                mission.mission_id,
                mission.status.value,
                mission.revision,
                mission.event_sequence,
                mission.model_dump_json(),
            ),
        )

    def _delete_children(self, mission_id: str) -> None:
        for table in CHILD_TABLES:
            self._connection.execute(
                f"DELETE FROM {table} WHERE mission_id = ?",  # noqa: S608
                (mission_id,),
            )

    def _write_children(self, snapshot: RuntimeSnapshot) -> None:
        mission_id = snapshot.mission.mission_id
        if snapshot.world is not None:
            self._connection.execute(
                "INSERT INTO simulator_world VALUES (?, ?, ?, ?)",
                (
                    mission_id,
                    snapshot.world.current_policy_id,
                    snapshot.world.vendor.status.value,
                    snapshot.world.model_dump_json(),
                ),
            )
        self._insert_positioned(
            "work_items",
            mission_id,
            snapshot.work_items,
            lambda item: (
                item.work_item_id,
                item.status.value,
                item.work_type,
            ),
        )
        self._insert_positioned(
            "commitments",
            mission_id,
            snapshot.commitments,
            lambda item: (
                item.commitment_id,
                item.status.value,
                item.event_type,
            ),
        )
        self._insert_positioned(
            "side_effects",
            mission_id,
            snapshot.side_effects,
            lambda item: (
                item.side_effect_id,
                item.idempotency_key,
                item.status.value,
            ),
        )
        self._insert_positioned(
            "inbox_messages",
            mission_id,
            snapshot.inbox,
            lambda item: (item.message_id, item.message_type),
        )
        self._insert_positioned(
            "outbox_messages",
            mission_id,
            snapshot.outbox,
            lambda item: (item.outbox_message_id, item.event_type),
        )
        for event in snapshot.audit_events:
            self._connection.execute(
                "INSERT INTO audit_events VALUES (?, ?, ?, ?, ?)",
                (
                    mission_id,
                    event.audit_event_id,
                    event.event_sequence,
                    event.event_type,
                    event.model_dump_json(),
                ),
            )
        self._connection.execute(
            "INSERT INTO graph_state VALUES (?, ?, ?)",
            (
                mission_id,
                json.dumps(snapshot.graph.cause_by_node_id, sort_keys=True),
                json.dumps(snapshot.graph.metadata, sort_keys=True),
            ),
        )
        self._insert_graph_dict(
            "world_artifacts",
            mission_id,
            snapshot.graph.artifacts.values(),
            lambda item: (
                item.artifact_id,
                item.logical_key,
                item.status.value,
            ),
        )
        self._insert_graph_dict(
            "evidence_nodes",
            mission_id,
            snapshot.graph.evidences.values(),
            lambda item: (item.evidence_id, item.kind, item.status.value),
        )
        self._insert_graph_dict(
            "decisions",
            mission_id,
            snapshot.graph.decisions.values(),
            lambda item: (
                item.decision_id,
                item.decision_type,
                item.status.value,
            ),
        )
        self._insert_graph_dict(
            "actions",
            mission_id,
            snapshot.graph.actions.values(),
            lambda item: (
                item.action_id,
                item.action_type,
                item.status.value,
            ),
        )
        self._insert_positioned(
            "dependency_edges",
            mission_id,
            snapshot.graph.edges,
            lambda item: (item.edge_id,),
        )
        self._insert_positioned(
            "graph_events",
            mission_id,
            snapshot.graph.events,
            lambda item: (item.event_id,),
        )
        self._insert_positioned(
            "dispatch_records",
            mission_id,
            snapshot.graph.dispatches,
            lambda item: (item.dispatch_id,),
        )

    def _load_world(self, mission_id: str) -> EnterpriseWorld | None:
        row = self._connection.execute(
            "SELECT payload FROM simulator_world WHERE mission_id = ?",
            (mission_id,),
        ).fetchone()
        return None if row is None else EnterpriseWorld.model_validate_json(row[0])

    def _insert_positioned(
        self,
        table: str,
        mission_id: str,
        items,  # type: ignore[no-untyped-def]
        columns,  # type: ignore[no-untyped-def]
    ) -> None:
        for position, item in enumerate(items):
            values = columns(item)
            placeholders = ", ".join("?" for _ in range(len(values) + 3))
            self._connection.execute(
                f"INSERT INTO {table} VALUES ({placeholders})",  # noqa: S608
                (mission_id, *values, position, item.model_dump_json()),
            )

    def _insert_graph_dict(
        self,
        table: str,
        mission_id: str,
        items,  # type: ignore[no-untyped-def]
        columns,  # type: ignore[no-untyped-def]
    ) -> None:
        for item in items:
            values = columns(item)
            placeholders = ", ".join("?" for _ in range(len(values) + 2))
            self._connection.execute(
                f"INSERT INTO {table} VALUES ({placeholders})",  # noqa: S608
                (mission_id, *values, item.model_dump_json()),
            )

    def _load_list(self, table, mission_id, model):  # type: ignore[no-untyped-def]
        rows = self._connection.execute(
            f"SELECT payload FROM {table} WHERE mission_id = ? ORDER BY position",  # noqa: S608
            (mission_id,),
        ).fetchall()
        return [model.model_validate_json(row[0]) for row in rows]

    def _load_dict(
        self,
        table,  # type: ignore[no-untyped-def]
        identity_column,  # type: ignore[no-untyped-def]
        mission_id,  # type: ignore[no-untyped-def]
        model,  # type: ignore[no-untyped-def]
    ):
        rows = self._connection.execute(
            f"SELECT {identity_column}, payload FROM {table} WHERE mission_id = ?",  # noqa: S608
            (mission_id,),
        ).fetchall()
        return {row[0]: model.model_validate_json(row[1]) for row in rows}

    def _load_audit(self, mission_id: str) -> list[AuditEvent]:
        rows = self._connection.execute(
            "SELECT payload FROM audit_events WHERE mission_id = ? ORDER BY event_sequence",
            (mission_id,),
        ).fetchall()
        return [AuditEvent.model_validate_json(row[0]) for row in rows]
