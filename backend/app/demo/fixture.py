from uuid import uuid4

from app.domain.models import (
    ActionNode,
    DecisionNode,
    DependencyEdge,
    DomainEvent,
    EvidenceNode,
    GraphSnapshot,
    RelationType,
    WorldArtifact,
)
from app.repository.protocol import GraphRepository


def seed_canonical_mission(
    repo: GraphRepository,
    mission_id: str | None = None,
) -> str:
    resolved_mission_id = mission_id or f"demo-{uuid4()}"
    snapshot = GraphSnapshot(
        mission_id=resolved_mission_id,
        artifacts={
            "policy-v12": WorldArtifact(
                artifact_id="policy-v12",
                artifact_type="SECURITY_POLICY",
                logical_key="security-policy",
                version="v12",
            )
        },
        evidences={
            "soc2-A31": EvidenceNode(
                evidence_id="soc2-A31",
                kind="SOC2_CONTROL",
                revision="A31",
            ),
            "financial-F7": EvidenceNode(
                evidence_id="financial-F7",
                kind="FINANCIAL_REPORT",
                revision="F7",
            ),
        },
        decisions={
            "D42": DecisionNode(
                decision_id="D42",
                decision_type="SECURITY_REVIEW",
                outcome="APPROVED",
            ),
            "D43": DecisionNode(
                decision_id="D43",
                decision_type="FINANCIAL_REVIEW",
                outcome="APPROVED",
            ),
            "D50": DecisionNode(
                decision_id="D50",
                decision_type="PROCUREMENT_REVIEW",
                outcome="APPROVED",
            ),
        },
        actions={
            "activate-vendor": ActionNode(
                action_id="activate-vendor",
                action_type="ACTIVATE_VENDOR",
            )
        },
        edges=[
            DependencyEdge(
                edge_id="policy-D42",
                from_node_id="policy-v12",
                to_node_id="D42",
                relation_type=RelationType.GOVERNED_BY,
            ),
            DependencyEdge(
                edge_id="soc2-D42",
                from_node_id="soc2-A31",
                to_node_id="D42",
                relation_type=RelationType.SUPPORTED_BY,
            ),
            DependencyEdge(
                edge_id="financial-D43",
                from_node_id="financial-F7",
                to_node_id="D43",
                relation_type=RelationType.SUPPORTED_BY,
            ),
            DependencyEdge(
                edge_id="D42-D50",
                from_node_id="D42",
                to_node_id="D50",
                relation_type=RelationType.REQUIRES,
            ),
            DependencyEdge(
                edge_id="D43-D50",
                from_node_id="D43",
                to_node_id="D50",
                relation_type=RelationType.REQUIRES,
            ),
            DependencyEdge(
                edge_id="D50-activate",
                from_node_id="D50",
                to_node_id="activate-vendor",
                relation_type=RelationType.AUTHORIZES,
            ),
        ],
    )
    repo.create_snapshot(snapshot)
    return resolved_mission_id


def seed_alternate_mission(
    repo: GraphRepository,
    mission_id: str | None = None,
) -> tuple[str, DomainEvent]:
    resolved_mission_id = mission_id or f"alternate-{uuid4()}"
    snapshot = GraphSnapshot(
        mission_id=resolved_mission_id,
        artifacts={
            "access-snapshot-v4": WorldArtifact(
                artifact_id="access-snapshot-v4",
                artifact_type="PERMISSION_SNAPSHOT",
                logical_key="release-access",
                version="v4",
            )
        },
        evidences={
            "budget-source": EvidenceNode(
                evidence_id="budget-source",
                kind="BUDGET",
                revision="2026-Q3",
            )
        },
        decisions={
            "risk-review-X": DecisionNode(
                decision_id="risk-review-X",
                decision_type="RISK_REVIEW",
                outcome="APPROVED",
            ),
            "budget-Y": DecisionNode(
                decision_id="budget-Y",
                decision_type="BUDGET_REVIEW",
                outcome="APPROVED",
            ),
            "release-Z": DecisionNode(
                decision_id="release-Z",
                decision_type="RELEASE_REVIEW",
                outcome="APPROVED",
            ),
        },
        actions={
            "publish-Q": ActionNode(
                action_id="publish-Q",
                action_type="PUBLISH_RELEASE",
            )
        },
        edges=[
            DependencyEdge(
                edge_id="access-risk",
                from_node_id="access-snapshot-v4",
                to_node_id="risk-review-X",
                relation_type=RelationType.GOVERNED_BY,
            ),
            DependencyEdge(
                edge_id="budget-source-budget",
                from_node_id="budget-source",
                to_node_id="budget-Y",
                relation_type=RelationType.SUPPORTED_BY,
            ),
            DependencyEdge(
                edge_id="risk-release",
                from_node_id="risk-review-X",
                to_node_id="release-Z",
                relation_type=RelationType.REQUIRES,
            ),
            DependencyEdge(
                edge_id="budget-release",
                from_node_id="budget-Y",
                to_node_id="release-Z",
                relation_type=RelationType.REQUIRES,
            ),
            DependencyEdge(
                edge_id="release-publish",
                from_node_id="release-Z",
                to_node_id="publish-Q",
                relation_type=RelationType.AUTHORIZES,
            ),
        ],
    )
    repo.create_snapshot(snapshot)
    event = DomainEvent(
        event_id="alternate-artifact-change",
        event_type="permission.version.changed",
        payload={
            "logical_key": "release-access",
            "old_artifact_id": "access-snapshot-v4",
            "new_artifact_id": "access-snapshot-v5",
            "old_version": "v4",
            "new_version": "v5",
        },
    )
    return resolved_mission_id, event
