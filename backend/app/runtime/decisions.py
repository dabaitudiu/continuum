from app.domain.models import (
    DecisionNode,
    DecisionStatus,
    DependencyEdge,
    GraphSnapshot,
)
from app.runtime.errors import RuntimeDomainError


class DecisionService:
    @staticmethod
    def supersede(
        graph: GraphSnapshot,
        *,
        old_id: str,
        new_id: str,
        outcome: str,
    ) -> GraphSnapshot:
        if old_id not in graph.decisions:
            raise RuntimeDomainError(
                "DECISION_NOT_FOUND",
                f"decision does not exist: {old_id}",
            )
        if new_id in graph.decisions:
            raise RuntimeDomainError(
                "DECISION_ALREADY_EXISTS",
                f"decision already exists: {new_id}",
            )

        old = graph.decisions[old_id]
        if old.status not in {
            DecisionStatus.STALE,
            DecisionStatus.REVALIDATING,
        }:
            raise RuntimeDomainError(
                "INVALID_DECISION_TRANSITION",
                f"cannot supersede decision from {old.status}",
            )

        result = graph.model_copy(deep=True)
        result.decisions[old_id].status = DecisionStatus.SUPERSEDED
        result.decisions[new_id] = DecisionNode(
            decision_id=new_id,
            decision_type=old.decision_type,
            outcome=outcome,
            status=DecisionStatus.VALID,
            supersedes_decision_id=old_id,
            execution_count=1,
        )

        incoming_edges: list[DependencyEdge] = []
        for edge in result.edges:
            if edge.from_node_id == old_id:
                edge.from_node_id = new_id
            elif edge.to_node_id == old_id:
                incoming_edges.append(
                    edge.model_copy(
                        update={
                            "edge_id": f"{edge.edge_id}:{new_id}",
                            "to_node_id": new_id,
                        },
                        deep=True,
                    )
                )
        result.edges.extend(incoming_edges)
        return result
