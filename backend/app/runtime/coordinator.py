from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from app.agents.contracts import AgentOutcome
from app.agents.service import MissionAgentReasoner
from app.demo.runtime_fixture import seed_runtime_demo
from app.domain.invalidation import InvalidationService
from app.domain.models import (
    ActionStatus,
    DependencyEdge,
    DomainEvent,
    EvidenceNode,
    RelationType,
)
from app.repository.memory import InMemoryGraphRepository
from app.repository.runtime_protocol import RuntimeRepository
from app.runtime.commitments import CommitmentService
from app.runtime.entities import (
    AuditEvent,
    Commitment,
    CommitmentStatus,
    EnterpriseArtifact,
    ExecutionMode,
    InboxRecord,
    Mission,
    MissionStatus,
    OutboxMessage,
    RuntimeEvent,
    RuntimeSnapshot,
    VendorStatus,
    WorkItem,
    WorkStatus,
)
from app.runtime.decisions import DecisionService
from app.runtime.errors import RuntimeDomainError
from app.runtime.mutations import RuntimeMutation
from app.runtime.side_effects import SideEffectLedger
from app.runtime.state_machine import MissionStateMachine, WorkStateMachine


class CommandResult(BaseModel):
    snapshot: RuntimeSnapshot
    duplicate: bool = False
    result: dict[str, Any] = Field(default_factory=dict)


class RuntimeCoordinator:
    def __init__(
        self,
        repository: RuntimeRepository,
        agent_reasoner: MissionAgentReasoner | None = None,
    ) -> None:
        self._repository = repository
        self._agent_reasoner = agent_reasoner

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

    def list_recent(self, limit: int) -> list[RuntimeSnapshot]:
        return self._repository.list_recent(limit)

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
        agent_events: list[tuple[str, dict[str, Any]]] = []
        world = snapshot.world.model_copy(deep=True) if snapshot.world else None
        if self._agent_reasoner is not None:
            vendor_proposal = self._agent_reasoner.review_vendor(
                snapshot,
                f"{mission_id}:work:vendor-intake",
            )
            security_proposal = self._agent_reasoner.review_security(
                snapshot,
                f"{mission_id}:work:security_baseline",
            )
            procurement_proposal = self._agent_reasoner.review_procurement(
                snapshot,
                f"{mission_id}:work:procurement-baseline",
            )
            self._require_agent_outcome(vendor_proposal.outcome, AgentOutcome.COMPLETE)
            self._require_agent_outcome(security_proposal.outcome, AgentOutcome.APPROVED)
            self._require_agent_outcome(procurement_proposal.outcome, AgentOutcome.APPROVED)
            if world is not None:
                world.execution_mode = ExecutionMode.GOOGLE_ADK_GEMINI
            agent_events = [
                self._agent_audit("vendor-agent", vendor_proposal),
                self._agent_audit("security-agent", security_proposal),
                self._agent_audit("procurement-agent", procurement_proposal),
            ]
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

        completed_work: list[WorkItem] = []
        for work_type, agent in (
            ("SECURITY_BASELINE", "security-agent"),
            ("FINANCIAL_REVIEW", "procurement-agent"),
        ):
            item = WorkItem(
                work_item_id=f"{mission_id}:work:{work_type.lower()}",
                mission_id=mission_id,
                work_type=work_type,
                target_agent=agent,
            )
            item = WorkStateMachine.transition(item, WorkStatus.DISPATCHED)
            item = WorkStateMachine.transition(item, WorkStatus.RUNNING)
            completed_work.append(
                WorkStateMachine.transition(item, WorkStatus.SUCCEEDED)
            )

        commitment_id = f"{mission_id}:commitment:activation-window"
        procurement = WorkItem(
            work_item_id=f"{mission_id}:work:procurement-baseline",
            mission_id=mission_id,
            work_type="PROCUREMENT_BASELINE",
            target_agent="procurement-agent",
            commitment_ids=[commitment_id],
        )
        procurement = WorkStateMachine.transition(procurement, WorkStatus.DISPATCHED)
        procurement = WorkStateMachine.transition(procurement, WorkStatus.RUNNING)
        procurement = WorkStateMachine.transition(
            procurement,
            WorkStatus.WAITING,
            has_open_commitment=True,
        )
        commitment = Commitment(
            commitment_id=commitment_id,
            mission_id=mission_id,
            work_item_id=procurement.work_item_id,
            event_type="procurement.activation.window.opened",
            predicate={"vendor_id": snapshot.mission.subject_id},
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
                *agent_events,
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
            world=world,
            work_upserts=[intake, *completed_work, procurement],
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

    def upgrade_policy(self, mission_id: str, event_id: str) -> CommandResult:
        duplicate = self._duplicate(mission_id, event_id)
        if duplicate is not None:
            return duplicate
        snapshot = self._repository.load(mission_id)
        if snapshot.world is None:
            raise RuntimeDomainError("SIMULATOR_NOT_AVAILABLE", "mission has no enterprise world")
        if snapshot.mission.status is not MissionStatus.WAITING:
            raise RuntimeDomainError(
                "POLICY_UPGRADE_NOT_AVAILABLE",
                f"cannot inject policy from {snapshot.mission.status}",
            )

        event = DomainEvent(
            event_id=event_id,
            event_type="policy.version.changed",
            payload={
                "logical_key": "security-policy",
                "old_artifact_id": "policy-v12",
                "new_artifact_id": "policy-v13",
                "old_version": "v12",
                "new_version": "v13",
            },
        )
        graph_repo = InMemoryGraphRepository()
        graph_repo.create_snapshot(snapshot.graph)
        graph = InvalidationService(graph_repo).process_artifact_change(
            mission_id,
            event,
        )

        world = snapshot.world.model_copy(deep=True)
        world.current_policy_id = "policy-v13"
        world.artifacts["policy-v13"] = EnterpriseArtifact(
            artifact_id="policy-v13",
            artifact_type="SECURITY_POLICY",
            version="v13",
            metadata={"pen_test_required": True},
        )
        activation = next(
            item
            for item in snapshot.commitments
            if item.event_type == "procurement.activation.window.opened"
            and item.status is CommitmentStatus.OPEN
        )
        cancelled_commitment = CommitmentService.cancel(activation)
        activation_work = next(
            item for item in snapshot.work_items
            if item.work_item_id == activation.work_item_id
        )
        cancelled_work = WorkStateMachine.transition(
            activation_work,
            WorkStatus.CANCELLED,
        )
        security_work = WorkItem(
            work_item_id=f"{mission_id}:work:security-revalidation",
            mission_id=mission_id,
            work_type="SECURITY_REVALIDATION",
            target_agent="security-agent",
            input_refs=["policy-v13", "soc2-A31", "vendor-profile-r7"],
        )
        mission = MissionStateMachine.transition(
            snapshot.mission,
            MissionStatus.REVALIDATING,
        )
        result = {
            "mission_id": mission_id,
            "status": mission.status.value,
            "stale_decision_ids": ["D42", "D50"],
            "preserved_decision_ids": ["D43"],
        }
        audit, outbox = self._records(
            snapshot.mission,
            event_id,
            [
                ("policy.version.changed", event.payload),
                ("decision.stale", {"decision_id": "D42", "cause_artifact_id": "policy-v12"}),
                ("decision.stale", {"decision_id": "D50", "cause_artifact_id": "D42"}),
                ("commitment.cancelled", {"commitment_id": activation.commitment_id}),
                ("mission.revalidating", {"status": mission.status.value}),
            ],
        )
        committed = self._repository.commit(
            mission_id,
            snapshot.mission.revision,
            RuntimeMutation(
                mission=mission,
                world=world,
                graph=graph,
                work_upserts=[cancelled_work, security_work],
                commitment_upserts=[cancelled_commitment],
                audit_appends=audit,
                inbox_completion=InboxRecord(
                    mission_id=mission_id,
                    message_id=event_id,
                    message_type="policy.version.changed",
                    result=result,
                ),
                outbox_appends=outbox,
            ),
        )
        return CommandResult(snapshot=committed, result=result)

    def revalidate_affected_branch(
        self,
        mission_id: str,
        request_id: str,
    ) -> CommandResult:
        duplicate = self._duplicate(mission_id, request_id)
        if duplicate is not None:
            return duplicate
        snapshot = self._repository.load(mission_id)
        if snapshot.mission.status is not MissionStatus.REVALIDATING:
            raise RuntimeDomainError(
                "REVALIDATION_NOT_AVAILABLE",
                f"cannot revalidate from {snapshot.mission.status}",
            )
        work = next(
            item for item in snapshot.work_items
            if item.work_type == "SECURITY_REVALIDATION"
        )
        work = WorkStateMachine.transition(work, WorkStatus.DISPATCHED)
        work = WorkStateMachine.transition(work, WorkStatus.RUNNING)
        execution_mode = (
            snapshot.world.execution_mode.value
            if snapshot.world is not None
            else ExecutionMode.LOCAL_DETERMINISTIC.value
        )
        explanation = "Policy v13 requires PEN_TEST evidence."
        dependency_refs = ["policy-v13", "vendor-profile-r7"]
        if self._agent_reasoner is not None:
            proposal = self._agent_reasoner.review_security(snapshot, work.work_item_id)
            self._require_agent_outcome(
                proposal.outcome,
                AgentOutcome.MISSING_EVIDENCE,
            )
            if proposal.missing_document_type != "PEN_TEST":
                raise RuntimeDomainError(
                    "AGENT_RESULT_INVALID",
                    "security agent must request PEN_TEST under policy v13",
                )
            explanation = proposal.explanation
            dependency_refs = proposal.dependency_refs
        commitment_id = f"{mission_id}:commitment:pen-test"
        commitment = Commitment(
            commitment_id=commitment_id,
            mission_id=mission_id,
            work_item_id=work.work_item_id,
            event_type="vendor.document.uploaded",
            predicate={"vendor_id": "ACME", "document_type": "PEN_TEST"},
        )
        work = work.model_copy(update={"commitment_ids": [commitment_id]}, deep=True)
        work = WorkStateMachine.transition(
            work,
            WorkStatus.WAITING,
            has_open_commitment=True,
        )
        mission = MissionStateMachine.transition(snapshot.mission, MissionStatus.WAITING)
        result = {
            "mission_id": mission_id,
            "status": mission.status.value,
            "execution_mode": execution_mode,
            "missing_evidence": "PEN_TEST",
            "explanation": explanation,
            "dependency_refs": dependency_refs,
        }
        audit, outbox = self._records(
            snapshot.mission,
            request_id,
            [
                ("work.dispatched", {"work_item_id": work.work_item_id, "target_agent": "security-agent"}),
                ("agent.result.accepted", {"agent_id": "security-agent", "outcome": "MISSING_EVIDENCE", "execution_mode": execution_mode, "dependency_refs": dependency_refs, "explanation": explanation}),
                ("commitment.created", {"commitment_id": commitment_id, "event_type": commitment.event_type}),
                ("mission.waiting", {"status": mission.status.value, "commitment_id": commitment_id}),
            ],
        )
        committed = self._repository.commit(
            mission_id,
            snapshot.mission.revision,
            RuntimeMutation(
                mission=mission,
                work_upserts=[work],
                commitment_upserts=[commitment],
                audit_appends=audit,
                inbox_completion=InboxRecord(
                    mission_id=mission_id,
                    message_id=request_id,
                    message_type="mission.revalidate",
                    result=result,
                ),
                outbox_appends=outbox,
            ),
        )
        return CommandResult(snapshot=committed, result=result)

    def upload_pen_test(self, mission_id: str, event_id: str) -> CommandResult:
        duplicate = self._duplicate(mission_id, event_id)
        if duplicate is not None:
            return duplicate
        snapshot = self._repository.load(mission_id)
        if snapshot.world is None:
            raise RuntimeDomainError("SIMULATOR_NOT_AVAILABLE", "mission has no enterprise world")
        event = DomainEvent(
            event_id=event_id,
            event_type="vendor.document.uploaded",
            payload={
                "vendor_id": "ACME",
                "document_id": "pen-test-P9",
                "document_type": "PEN_TEST",
            },
        )
        commitment = next(
            (
                item for item in snapshot.commitments
                if CommitmentService.match(item, event)
            ),
            None,
        )
        if commitment is None:
            raise RuntimeDomainError(
                "PEN_TEST_NOT_AWAITED",
                "no open penetration-test commitment matches this event",
            )
        satisfied = CommitmentService.satisfy(commitment, event)
        security_work = next(
            item for item in snapshot.work_items
            if item.work_item_id == commitment.work_item_id
        )
        security_work = WorkStateMachine.transition(security_work, WorkStatus.PENDING)
        security_work = WorkStateMachine.transition(security_work, WorkStatus.DISPATCHED)
        security_work = WorkStateMachine.transition(security_work, WorkStatus.RUNNING)
        security_work = WorkStateMachine.transition(security_work, WorkStatus.SUCCEEDED)

        world = snapshot.world.model_copy(deep=True)
        world.artifacts["pen-test-P9"] = EnterpriseArtifact(
            artifact_id="pen-test-P9",
            artifact_type="DOCUMENT",
            version="P9",
            metadata={"document_type": "PEN_TEST"},
        )
        world.documents.append("pen-test-P9")

        graph = snapshot.graph.model_copy(deep=True)
        graph.events.append(event)
        graph.evidences["pen-test-P9"] = EvidenceNode(
            evidence_id="pen-test-P9",
            kind="PEN_TEST",
            revision="P9",
        )
        reasoning_snapshot = snapshot.model_copy(
            update={"world": world, "graph": graph},
            deep=True,
        )
        security_explanation = "Policy v13 requirements are now satisfied."
        if self._agent_reasoner is not None:
            security_proposal = self._agent_reasoner.review_security(
                reasoning_snapshot,
                security_work.work_item_id,
            )
            self._require_agent_outcome(
                security_proposal.outcome,
                AgentOutcome.APPROVED,
            )
            security_explanation = security_proposal.explanation
        graph = DecisionService.supersede(graph, old_id="D42", new_id="D57", outcome="APPROVED")
        graph.edges = [
            edge for edge in graph.edges
            if not (edge.from_node_id == "policy-v12" and edge.to_node_id == "D57")
        ]
        graph.edges.extend(
            [
                DependencyEdge(
                    edge_id="policy-v13-D57",
                    from_node_id="policy-v13",
                    to_node_id="D57",
                    relation_type=RelationType.GOVERNED_BY,
                ),
                DependencyEdge(
                    edge_id="pen-test-D57",
                    from_node_id="pen-test-P9",
                    to_node_id="D57",
                    relation_type=RelationType.SUPPORTED_BY,
                ),
            ]
        )
        graph = DecisionService.supersede(graph, old_id="D50", new_id="D58", outcome="APPROVED")
        graph.actions["activate-vendor"].status = ActionStatus.READY

        procurement_explanation = "Current Security and Financial decisions authorize activation."
        if self._agent_reasoner is not None:
            procurement_snapshot = snapshot.model_copy(
                update={"world": world, "graph": graph},
                deep=True,
            )
            procurement_proposal = self._agent_reasoner.review_procurement(
                procurement_snapshot,
                f"{mission_id}:work:procurement-resume",
            )
            self._require_agent_outcome(
                procurement_proposal.outcome,
                AgentOutcome.APPROVED,
            )
            procurement_explanation = procurement_proposal.explanation

        procurement = WorkItem(
            work_item_id=f"{mission_id}:work:procurement-resume",
            mission_id=mission_id,
            work_type="PROCUREMENT_RESUME",
            target_agent="procurement-agent",
            input_refs=["D57", "D43"],
        )
        procurement = WorkStateMachine.transition(procurement, WorkStatus.DISPATCHED)
        procurement = WorkStateMachine.transition(procurement, WorkStatus.RUNNING)
        procurement = WorkStateMachine.transition(procurement, WorkStatus.SUCCEEDED)

        effect = SideEffectLedger.intent(
            side_effect_id=f"{mission_id}:effect:activate-vendor",
            mission_id=mission_id,
            effect_type="ACTIVATE_VENDOR",
            idempotency_key=f"activate:{mission_id}:ACME",
            authorization_decision_id="D58",
            request={"vendor_id": "ACME"},
        )
        effect = SideEffectLedger.begin(effect, graph.decisions["D58"].status)
        effect = SideEffectLedger.commit(effect, result={"vendor_status": "ACTIVE"})
        world.vendor.status = VendorStatus.ACTIVE
        running = MissionStateMachine.transition(snapshot.mission, MissionStatus.RUNNING)
        mission = MissionStateMachine.transition(running, MissionStatus.COMPLETED)
        result = {
            "mission_id": mission_id,
            "status": mission.status.value,
            "vendor_status": world.vendor.status.value,
            "matched_commitment_ids": [commitment.commitment_id],
        }
        audit, outbox = self._records(
            snapshot.mission,
            event_id,
            [
                ("vendor.document.uploaded", event.payload),
                ("commitment.satisfied", {"commitment_id": commitment.commitment_id, "event_id": event_id}),
                ("agent.result.accepted", {"agent_id": "security-agent", "outcome": "APPROVED", "execution_mode": world.execution_mode.value, "explanation": security_explanation}),
                ("decision.superseded", {"old_decision_id": "D42", "new_decision_id": "D57"}),
                ("agent.result.accepted", {"agent_id": "procurement-agent", "outcome": "APPROVED", "execution_mode": world.execution_mode.value, "explanation": procurement_explanation}),
                ("decision.superseded", {"old_decision_id": "D50", "new_decision_id": "D58"}),
                ("side_effect.committed", {"side_effect_id": effect.side_effect_id, "effect_type": effect.effect_type}),
                ("mission.completed", {"status": mission.status.value, "vendor_status": "ACTIVE"}),
            ],
        )
        committed = self._repository.commit(
            mission_id,
            snapshot.mission.revision,
            RuntimeMutation(
                mission=mission,
                world=world,
                graph=graph,
                work_upserts=[security_work, procurement],
                commitment_upserts=[satisfied],
                side_effect_upserts=[effect],
                audit_appends=audit,
                inbox_completion=InboxRecord(
                    mission_id=mission_id,
                    message_id=event_id,
                    message_type="vendor.document.uploaded",
                    result=result,
                ),
                outbox_appends=outbox,
            ),
        )
        return CommandResult(snapshot=committed, result=result)

    def get(self, mission_id: str) -> RuntimeSnapshot:
        return self._repository.load(mission_id)

    @staticmethod
    def _require_agent_outcome(actual: AgentOutcome, expected: AgentOutcome) -> None:
        if actual is not expected:
            raise RuntimeDomainError(
                "AGENT_RESULT_INVALID",
                f"expected agent outcome {expected}, found {actual}",
            )

    @staticmethod
    def _agent_audit(agent_id: str, proposal: Any) -> tuple[str, dict[str, Any]]:
        return (
            "agent.result.accepted",
            {
                "agent_id": agent_id,
                "outcome": proposal.outcome.value,
                "execution_mode": ExecutionMode.GOOGLE_ADK_GEMINI.value,
                "dependency_refs": proposal.dependency_refs,
                "explanation": proposal.explanation,
            },
        )

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
