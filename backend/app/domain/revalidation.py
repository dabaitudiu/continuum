from app.domain.invalidation import DECISION_PROPAGATION_RELATIONS
from app.domain.models import (
    ActionStatus,
    DecisionStatus,
    DispatchRecord,
    RevalidationPlan,
)
from app.repository.protocol import GraphRepository


class RevalidationService:
    def __init__(self, repository: GraphRepository) -> None:
        self._repository = repository

    def plan(self, mission_id: str) -> RevalidationPlan:
        snapshot = self._repository.get_snapshot(mission_id)
        stale_ids = {
            decision_id
            for decision_id, decision in snapshot.decisions.items()
            if decision.status is DecisionStatus.STALE
        }
        waiting_ids = {
            edge.to_node_id
            for edge in snapshot.edges
            if edge.critical
            and edge.relation_type in DECISION_PROPAGATION_RELATIONS
            and edge.from_node_id in stale_ids
            and edge.to_node_id in stale_ids
        }
        blocked_action_ids = {
            action_id
            for action_id, action in snapshot.actions.items()
            if action.status is ActionStatus.BLOCKED
        }
        explained_node_ids = stale_ids | blocked_action_ids

        return RevalidationPlan(
            stale_decision_ids=sorted(stale_ids),
            runnable_decision_ids=sorted(stale_ids - waiting_ids),
            waiting_decision_ids=sorted(waiting_ids),
            blocked_action_ids=sorted(blocked_action_ids),
            retained_decision_ids=sorted(
                decision_id
                for decision_id, decision in snapshot.decisions.items()
                if decision.status is DecisionStatus.VALID
            ),
            cause_by_node_id={
                node_id: snapshot.cause_by_node_id[node_id]
                for node_id in sorted(explained_node_ids)
                if node_id in snapshot.cause_by_node_id
            },
        )

    def dispatch(
        self,
        mission_id: str,
        request_id: str,
    ) -> list[DispatchRecord]:
        if self._repository.has_processed_request(mission_id, request_id):
            snapshot = self._repository.get_snapshot(mission_id)
            return [
                record.model_copy(deep=True)
                for record in snapshot.dispatches
                if record.request_id == request_id
            ]

        plan = self.plan(mission_id)
        snapshot = self._repository.get_snapshot(mission_id)
        records: list[DispatchRecord] = []
        for decision_id in plan.runnable_decision_ids:
            decision = snapshot.decisions[decision_id]
            decision.status = DecisionStatus.REVALIDATING
            decision.execution_count += 1
            record = DispatchRecord(
                dispatch_id=f"dispatch:{request_id}:{decision_id}",
                request_id=request_id,
                decision_id=decision_id,
                work_type="REVALIDATE_DECISION",
            )
            snapshot.dispatches.append(record)
            records.append(record.model_copy(deep=True))

        self._repository.save_snapshot(snapshot)
        self._repository.mark_request_processed(mission_id, request_id)
        return records
