from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from app.demo.runtime_fixture import seed_runtime_demo
from app.domain.models import DomainEvent
from app.repository.runtime_protocol import RuntimeRepository
from app.runtime.commitments import CommitmentService
from app.runtime.entities import (
    AuditEvent,
    Commitment,
    CommitmentStatus,
    InboxRecord,
    Mission,
    MissionStatus,
    OutboxMessage,
    RuntimeEvent,
    RuntimeSnapshot,
    WorkItem,
    WorkStatus,
)
from app.runtime.errors import RuntimeDomainError
from app.runtime.mutations import RuntimeMutation
from app.runtime.state_machine import MissionStateMachine, WorkStateMachine


class CommandResult(BaseModel):
    snapshot: RuntimeSnapshot
    duplicate: bool = False
    result: dict[str, Any] = Field(default_factory=dict)


class RuntimeCoordinator:
    def __init__(self, repository: RuntimeRepository) -> None:
        self._repository = repository

    def create_demo(self, request_id: str) -> CommandResult:
        seeded = seed_runtime_demo(request_id)
        mission_id = seeded.mission.mission_id
        try:
            existing = self._repository.load(mission_id)
        except RuntimeDomainError as error:
            if error.code != "MISSION_NOT_FOUND":
                raise
        else:
            inbox = self._repository.find_inbox(mission_id, request_id)
            if inbox is not None:
                return CommandResult(
                    snapshot=existing,
                    duplicate=True,
                    result=inbox.result,
                )
            raise RuntimeDomainError(
                "MISSION_ALREADY_EXISTS",
                f"mission namespace already exists: {mission_id}",
            )

        try:
            self._repository.create(seeded)
        except RuntimeDomainError as error:
            if error.code != "MISSION_ALREADY_EXISTS":
                raise
            existing = self._repository.load(mission_id)
            inbox = self._repository.find_inbox(mission_id, request_id)
            if inbox is None:
                raise
            return CommandResult(
                snapshot=existing,
                duplicate=True,
                result=inbox.result,
            )
        return CommandResult(
            snapshot=seeded.model_copy(deep=True),
            result=seeded.inbox[0].result,
        )

    def start(self, mission_id: str, request_id: str) -> CommandResult:
        duplicate = self._duplicate(mission_id, request_id)
        if duplicate is not None:
            return duplicate
        snapshot = self._repository.load(mission_id)
        if snapshot.mission.status is not MissionStatus.CREATED:
            raise RuntimeDomainError(
                "INVALID_MISSION_TRANSITION",
                f"cannot start mission from {snapshot.mission.status}",
            )
        running = MissionStateMachine.transition(
            snapshot.mission,
            MissionStatus.RUNNING,
        )

        intake = next(
            item for item in snapshot.work_items if item.work_type == "VENDOR_INTAKE"
        )
        intake = WorkStateMachine.transition(intake, WorkStatus.DISPATCHED)
        intake = WorkStateMachine.transition(intake, WorkStatus.RUNNING)
        intake = WorkStateMachine.transition(intake, WorkStatus.SUCCEEDED)

        commitment_id = f"{mission_id}:commitment:pen-test"
        review = WorkItem(
            work_item_id=f"{mission_id}:work:review-pen-test",
            mission_id=mission_id,
            work_type="REVIEW_PEN_TEST",
            target_agent="security-agent",
            commitment_ids=[commitment_id],
        )
        review = WorkStateMachine.transition(review, WorkStatus.DISPATCHED)
        review = WorkStateMachine.transition(review, WorkStatus.RUNNING)
        review = WorkStateMachine.transition(
            review,
            WorkStatus.WAITING,
            has_open_commitment=True,
        )
        commitment = Commitment(
            commitment_id=commitment_id,
            mission_id=mission_id,
            work_item_id=review.work_item_id,
            event_type="vendor.document.uploaded",
            predicate={
                "vendor_id": snapshot.mission.subject_id,
                "document_type": "PEN_TEST",
            },
        )
        waiting = MissionStateMachine.transition(running, MissionStatus.WAITING)
        result = {
            "mission_id": mission_id,
            "status": waiting.status.value,
        }
        audit, outbox = self._records(
            snapshot.mission,
            request_id,
            [
                ("mission.started", {"status": MissionStatus.RUNNING.value}),
                (
                    "mission.waiting",
                    {
                        "status": MissionStatus.WAITING.value,
                        "commitment_id": commitment_id,
                    },
                ),
            ],
        )
        mutation = RuntimeMutation(
            mission=waiting,
            work_upserts=[intake, review],
            commitment_upserts=[commitment],
            audit_appends=audit,
            inbox_completion=InboxRecord(
                mission_id=mission_id,
                message_id=request_id,
                message_type="mission.start",
                result=result,
            ),
            outbox_appends=outbox,
        )
        committed = self._repository.commit(
            mission_id,
            snapshot.mission.revision,
            mutation,
        )
        return CommandResult(snapshot=committed, result=result)

    def process_event(self, event: RuntimeEvent) -> CommandResult:
        duplicate = self._duplicate(event.mission_id, event.event_id)
        if duplicate is not None:
            return duplicate
        snapshot = self._repository.load(event.mission_id)
        domain_event = DomainEvent(
            event_id=event.event_id,
            event_type=event.event_type,
            payload=event.payload,
        )
        matches = [
            commitment
            for commitment in snapshot.commitments
            if CommitmentService.match(commitment, domain_event)
        ]
        graph = snapshot.graph.model_copy(deep=True)
        graph.events.append(domain_event)

        if not matches:
            result: dict[str, Any] = {"matched_commitment_ids": []}
            audit, outbox = self._records(
                snapshot.mission,
                event.event_id,
                [
                    (
                        "event.ignored",
                        {
                            "event_id": event.event_id,
                            "event_type": event.event_type,
                        },
                    )
                ],
                correlation_id=event.correlation_id,
                trace_id=event.trace_id,
            )
            mutation = RuntimeMutation(
                mission=snapshot.mission,
                graph=graph,
                audit_appends=audit,
                inbox_completion=InboxRecord(
                    mission_id=event.mission_id,
                    message_id=event.event_id,
                    message_type=event.event_type,
                    result=result,
                ),
                outbox_appends=outbox,
            )
        else:
            satisfied = [
                CommitmentService.satisfy(commitment, domain_event)
                for commitment in matches
            ]
            work_by_id = {item.work_item_id: item for item in snapshot.work_items}
            resumed_work = [
                WorkStateMachine.transition(
                    work_by_id[commitment.work_item_id],
                    WorkStatus.PENDING,
                )
                for commitment in satisfied
            ]
            mission = snapshot.mission
            if mission.status is MissionStatus.WAITING:
                mission = MissionStateMachine.transition(
                    mission,
                    MissionStatus.RUNNING,
                )
            result = {
                "matched_commitment_ids": [
                    commitment.commitment_id for commitment in satisfied
                ]
            }
            event_specs = [
                (
                    "commitment.satisfied",
                    {
                        "commitment_id": commitment.commitment_id,
                        "event_id": event.event_id,
                    },
                )
                for commitment in satisfied
            ]
            if mission.status is MissionStatus.RUNNING:
                event_specs.append(
                    ("mission.resumed", {"status": MissionStatus.RUNNING.value})
                )
            audit, outbox = self._records(
                snapshot.mission,
                event.event_id,
                event_specs,
                correlation_id=event.correlation_id,
                trace_id=event.trace_id,
            )
            mutation = RuntimeMutation(
                mission=mission,
                work_upserts=resumed_work,
                commitment_upserts=satisfied,
                graph=graph,
                audit_appends=audit,
                inbox_completion=InboxRecord(
                    mission_id=event.mission_id,
                    message_id=event.event_id,
                    message_type=event.event_type,
                    result=result,
                ),
                outbox_appends=outbox,
            )

        committed = self._repository.commit(
            event.mission_id,
            snapshot.mission.revision,
            mutation,
        )
        return CommandResult(snapshot=committed, result=result)

    def get(self, mission_id: str) -> RuntimeSnapshot:
        return self._repository.load(mission_id)

    def timeline(self, mission_id: str) -> list[AuditEvent]:
        snapshot = self._repository.load(mission_id)
        return [
            event.model_copy(deep=True)
            for event in sorted(
                snapshot.audit_events,
                key=lambda event: event.event_sequence,
            )
        ]

    def commitments(self, mission_id: str) -> list[Commitment]:
        return [
            commitment.model_copy(deep=True)
            for commitment in self._repository.load(mission_id).commitments
        ]

    def _duplicate(
        self,
        mission_id: str,
        message_id: str,
    ) -> CommandResult | None:
        inbox = self._repository.find_inbox(mission_id, message_id)
        if inbox is None:
            return None
        return CommandResult(
            snapshot=self._repository.load(mission_id),
            duplicate=True,
            result=inbox.result,
        )

    @staticmethod
    def _records(
        mission: Mission,
        causation_id: str,
        specs: list[tuple[str, dict[str, Any]]],
        *,
        correlation_id: str | None = None,
        trace_id: str | None = None,
    ) -> tuple[list[AuditEvent], list[OutboxMessage]]:
        resolved_correlation = correlation_id or causation_id
        audit: list[AuditEvent] = []
        outbox: list[OutboxMessage] = []
        for offset, (event_type, payload) in enumerate(specs, start=1):
            event_sequence = mission.event_sequence + offset
            suffix = f"{causation_id}:{offset}"
            audit.append(
                AuditEvent(
                    audit_event_id=f"audit:{suffix}",
                    mission_id=mission.mission_id,
                    event_sequence=event_sequence,
                    event_type=event_type,
                    payload=payload,
                    correlation_id=resolved_correlation,
                    causation_id=causation_id,
                    trace_id=trace_id,
                )
            )
            outbox.append(
                OutboxMessage(
                    outbox_message_id=f"outbox:{suffix}",
                    mission_id=mission.mission_id,
                    event_type=event_type,
                    payload=payload,
                    correlation_id=resolved_correlation,
                    causation_id=causation_id,
                    trace_id=trace_id,
                )
            )
        return audit, outbox
