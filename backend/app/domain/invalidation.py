from collections import deque

from app.domain.models import (
    ActionStatus,
    ArtifactStatus,
    DecisionStatus,
    DomainEvent,
    GraphSnapshot,
    RelationType,
    WorldArtifact,
)
from app.repository.protocol import GraphRepository


DIRECT_INVALIDATION_RELATIONS = {
    RelationType.GOVERNED_BY,
    RelationType.SUPPORTED_BY,
    RelationType.DERIVED_FROM,
    RelationType.REQUIRES,
}

DECISION_PROPAGATION_RELATIONS = {
    RelationType.REQUIRES,
    RelationType.DERIVED_FROM,
}


class InvalidationService:
    def __init__(self, repository: GraphRepository) -> None:
        self._repository = repository

    def process_artifact_change(
        self,
        mission_id: str,
        event: DomainEvent,
    ) -> GraphSnapshot:
        if self._repository.has_processed_event(mission_id, event.event_id):
            return self._repository.get_snapshot(mission_id)

        snapshot = self._repository.get_snapshot(mission_id)
        old_artifact = self._validate_event(snapshot, event)
        payload = event.payload

        old_artifact.status = ArtifactStatus.SUPERSEDED
        snapshot.artifacts[payload["new_artifact_id"]] = WorldArtifact(
            artifact_id=payload["new_artifact_id"],
            artifact_type=old_artifact.artifact_type,
            logical_key=old_artifact.logical_key,
            version=payload["new_version"],
            supersedes_artifact_id=old_artifact.artifact_id,
            status=ArtifactStatus.CURRENT,
        )

        newly_stale = deque[str]()
        for edge in snapshot.edges:
            if (
                edge.from_node_id == old_artifact.artifact_id
                and edge.critical
                and edge.relation_type in DIRECT_INVALIDATION_RELATIONS
                and edge.to_node_id in snapshot.decisions
            ):
                decision = snapshot.decisions[edge.to_node_id]
                if decision.status is not DecisionStatus.STALE:
                    decision.status = DecisionStatus.STALE
                    snapshot.cause_by_node_id[decision.decision_id] = (
                        old_artifact.artifact_id
                    )
                    newly_stale.append(decision.decision_id)

        self._propagate(snapshot, newly_stale)
        snapshot.events.append(event.model_copy(deep=True))
        self._repository.save_snapshot(
            snapshot,
            processed_event_id=event.event_id,
        )
        return self._repository.get_snapshot(mission_id)

    def _validate_event(
        self,
        snapshot: GraphSnapshot,
        event: DomainEvent,
    ) -> WorldArtifact:
        required_fields = {
            "logical_key",
            "old_artifact_id",
            "new_artifact_id",
            "old_version",
            "new_version",
        }
        missing_fields = required_fields.difference(event.payload)
        if missing_fields:
            missing = ", ".join(sorted(missing_fields))
            raise ValueError(f"artifact change is missing fields: {missing}")

        old_artifact_id = event.payload["old_artifact_id"]
        try:
            old_artifact = snapshot.artifacts[old_artifact_id]
        except KeyError as error:
            raise ValueError(f"unknown old artifact: {old_artifact_id}") from error

        if old_artifact.logical_key != event.payload["logical_key"]:
            raise ValueError("artifact logical key does not match")
        if old_artifact.version != event.payload["old_version"]:
            raise ValueError("old artifact version does not match")
        if event.payload["new_artifact_id"] in snapshot.artifacts:
            raise ValueError("new artifact already exists")
        if old_artifact.status is not ArtifactStatus.CURRENT:
            raise ValueError("old artifact is not current")
        return old_artifact

    def _propagate(
        self,
        snapshot: GraphSnapshot,
        newly_stale: deque[str],
    ) -> None:
        visited: set[str] = set()
        while newly_stale:
            source_id = newly_stale.popleft()
            if source_id in visited:
                continue
            visited.add(source_id)

            for edge in snapshot.edges:
                if edge.from_node_id != source_id or not edge.critical:
                    continue

                if (
                    edge.to_node_id in snapshot.decisions
                    and edge.relation_type in DECISION_PROPAGATION_RELATIONS
                ):
                    decision = snapshot.decisions[edge.to_node_id]
                    if decision.status is not DecisionStatus.STALE:
                        decision.status = DecisionStatus.STALE
                        snapshot.cause_by_node_id[decision.decision_id] = source_id
                        newly_stale.append(decision.decision_id)
                elif (
                    edge.to_node_id in snapshot.actions
                    and edge.relation_type is RelationType.AUTHORIZES
                ):
                    action = snapshot.actions[edge.to_node_id]
                    action.status = ActionStatus.BLOCKED
                    snapshot.cause_by_node_id[action.action_id] = source_id
