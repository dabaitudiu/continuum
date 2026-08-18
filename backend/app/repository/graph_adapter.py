from app.domain.models import GraphSnapshot
from app.repository.runtime_protocol import RuntimeRepository
from app.runtime.entities import (
    AuditEvent,
    InboxRecord,
    Mission,
    OutboxMessage,
    RuntimeSnapshot,
)
from app.runtime.errors import RuntimeDomainError
from app.runtime.mutations import RuntimeMutation


class RuntimeGraphRepositoryAdapter:
    def __init__(self, runtime_repository: RuntimeRepository) -> None:
        self._runtime_repository = runtime_repository

    def create_snapshot(self, snapshot: GraphSnapshot) -> None:
        mission_id = snapshot.mission_id
        message_id = f"graph:create:{mission_id}"
        result = {"mission_id": mission_id, "status": "CREATED"}
        aggregate = RuntimeSnapshot(
            mission=Mission(mission_id=mission_id, event_sequence=1),
            graph=snapshot.model_copy(deep=True),
            inbox=[
                InboxRecord(
                    mission_id=mission_id,
                    message_id=message_id,
                    message_type="graph.create",
                    result=result,
                )
            ],
            audit_events=[
                AuditEvent(
                    audit_event_id=f"audit:{message_id}",
                    mission_id=mission_id,
                    event_sequence=1,
                    event_type="mission.created",
                    payload=result,
                    correlation_id=message_id,
                    causation_id=message_id,
                )
            ],
            outbox=[
                OutboxMessage(
                    outbox_message_id=f"outbox:{message_id}",
                    mission_id=mission_id,
                    event_type="mission.created",
                    payload=result,
                    correlation_id=message_id,
                    causation_id=message_id,
                )
            ],
        )
        try:
            self._runtime_repository.create(aggregate)
        except RuntimeDomainError as error:
            if error.code == "MISSION_ALREADY_EXISTS":
                raise ValueError(f"mission already exists: {mission_id}") from error
            raise

    def get_snapshot(self, mission_id: str) -> GraphSnapshot:
        try:
            return self._runtime_repository.load(mission_id).graph
        except RuntimeDomainError as error:
            if error.code == "MISSION_NOT_FOUND":
                raise KeyError(f"unknown mission: {mission_id}") from error
            raise

    def save_snapshot(
        self,
        snapshot: GraphSnapshot,
        *,
        processed_event_id: str | None = None,
        processed_request_id: str | None = None,
    ) -> None:
        if processed_event_id is not None and processed_request_id is not None:
            raise ValueError("a graph save can process either an event or a request")
        mission_id = snapshot.mission_id
        try:
            current = self._runtime_repository.load(mission_id)
        except RuntimeDomainError as error:
            if error.code == "MISSION_NOT_FOUND":
                raise KeyError(f"unknown mission: {mission_id}") from error
            raise

        message_id, message_type, audit_type = self._message_identity(
            current,
            processed_event_id=processed_event_id,
            processed_request_id=processed_request_id,
        )
        if self._runtime_repository.find_inbox(mission_id, message_id) is not None:
            return
        result = {"mission_id": mission_id, "revision": current.mission.revision + 1}
        sequence = current.mission.event_sequence + 1
        mutation = RuntimeMutation(
            mission=current.mission,
            graph=snapshot,
            audit_appends=[
                AuditEvent(
                    audit_event_id=f"audit:{message_id}",
                    mission_id=mission_id,
                    event_sequence=sequence,
                    event_type=audit_type,
                    payload=result,
                    correlation_id=message_id,
                    causation_id=message_id,
                )
            ],
            inbox_completion=InboxRecord(
                mission_id=mission_id,
                message_id=message_id,
                message_type=message_type,
                result=result,
            ),
            outbox_appends=[
                OutboxMessage(
                    outbox_message_id=f"outbox:{message_id}",
                    mission_id=mission_id,
                    event_type=audit_type,
                    payload=result,
                    correlation_id=message_id,
                    causation_id=message_id,
                )
            ],
        )
        self._runtime_repository.commit(
            mission_id,
            current.mission.revision,
            mutation,
        )

    def has_processed_event(self, mission_id: str, event_id: str) -> bool:
        return self._has_message(mission_id, f"graph:event:{event_id}")

    def mark_event_processed(self, mission_id: str, event_id: str) -> None:
        if not self.has_processed_event(mission_id, event_id):
            self.save_snapshot(
                self.get_snapshot(mission_id),
                processed_event_id=event_id,
            )

    def has_processed_request(self, mission_id: str, request_id: str) -> bool:
        return self._has_message(mission_id, f"graph:request:{request_id}")

    def mark_request_processed(self, mission_id: str, request_id: str) -> None:
        if not self.has_processed_request(mission_id, request_id):
            self.save_snapshot(
                self.get_snapshot(mission_id),
                processed_request_id=request_id,
            )

    def _has_message(self, mission_id: str, message_id: str) -> bool:
        try:
            return self._runtime_repository.find_inbox(mission_id, message_id) is not None
        except RuntimeDomainError as error:
            if error.code == "MISSION_NOT_FOUND":
                raise KeyError(f"unknown mission: {mission_id}") from error
            raise

    @staticmethod
    def _message_identity(
        current: RuntimeSnapshot,
        *,
        processed_event_id: str | None,
        processed_request_id: str | None,
    ) -> tuple[str, str, str]:
        if processed_event_id is not None:
            return (
                f"graph:event:{processed_event_id}",
                "graph.event",
                "graph.event.applied",
            )
        if processed_request_id is not None:
            return (
                f"graph:request:{processed_request_id}",
                "graph.request",
                "graph.request.applied",
            )
        revision = current.mission.revision + 1
        return (
            f"graph:save:{revision}",
            "graph.save",
            "graph.snapshot.saved",
        )
