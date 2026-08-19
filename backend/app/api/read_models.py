from typing import Any

from app.domain.models import ActionStatus, DecisionStatus, GraphSnapshot, RevalidationPlan
from app.repository.memory import InMemoryGraphRepository
from app.domain.revalidation import RevalidationService
from app.runtime.entities import CommitmentStatus, MissionStatus, RuntimeSnapshot, VendorStatus


def graph_read_model(
    snapshot: GraphSnapshot,
    plan: RevalidationPlan,
) -> dict[str, Any]:
    nodes: list[dict[str, Any]] = []
    nodes.extend(
        {
            "id": node.artifact_id,
            "kind": "artifact",
            "label": node.logical_key,
            **node.model_dump(mode="json"),
        }
        for node in snapshot.artifacts.values()
    )
    nodes.extend(
        {
            **node.model_dump(mode="json"),
            "id": node.evidence_id,
            "kind": "evidence",
            "label": node.kind,
            "evidence_kind": node.kind,
        }
        for node in snapshot.evidences.values()
    )
    nodes.extend(
        {
            "id": node.claim_id,
            "kind": "claim",
            "label": node.statement,
            **node.model_dump(mode="json"),
        }
        for node in snapshot.claims.values()
    )
    nodes.extend(
        {
            "id": node.decision_id,
            "kind": "decision",
            "label": node.decision_type,
            **node.model_dump(mode="json"),
        }
        for node in snapshot.decisions.values()
    )
    nodes.extend(
        {
            "id": node.action_id,
            "kind": "action",
            "label": node.action_type,
            **node.model_dump(mode="json"),
        }
        for node in snapshot.actions.values()
    )

    if any(
        decision.status is DecisionStatus.REVALIDATING
        for decision in snapshot.decisions.values()
    ):
        phase = "REVALIDATING"
    elif snapshot.events:
        phase = "DRIFTED"
    else:
        phase = "INITIAL"

    return {
        "mission_id": snapshot.mission_id,
        "phase": phase,
        "summary": {
            "stale": sum(
                decision.status is DecisionStatus.STALE
                for decision in snapshot.decisions.values()
            ),
            "preserved": sum(
                decision.status is DecisionStatus.VALID
                for decision in snapshot.decisions.values()
            ),
            "blocked": sum(
                action.status is ActionStatus.BLOCKED
                for action in snapshot.actions.values()
            ),
        },
        "nodes": sorted(nodes, key=lambda node: node["id"]),
        "edges": [edge.model_dump(mode="json") for edge in snapshot.edges],
        "plan": plan.model_dump(mode="json"),
        "causes": dict(sorted(snapshot.cause_by_node_id.items())),
        "events": [event.model_dump(mode="json") for event in snapshot.events],
        "dispatches": [
            dispatch.model_dump(mode="json") for dispatch in snapshot.dispatches
        ],
    }


def control_read_model(snapshot: RuntimeSnapshot) -> dict[str, Any]:
    world = snapshot.world
    if world is None:
        raise ValueError("mission has no enterprise simulator world")
    phase, next_action = _phase(snapshot)
    plan = _plan(snapshot.graph)
    graph = graph_read_model(snapshot.graph, plan)
    decision = snapshot.graph.decisions
    open_commitment = next(
        (
            item for item in snapshot.commitments
            if item.status is CommitmentStatus.OPEN
        ),
        None,
    )
    lanes = [
        {
            "agent_id": "vendor-agent",
            "label": "VENDOR AGENT",
            "status": "SUCCEEDED" if phase != "CREATED" else "PENDING",
            "checkpoints": [
                {"id": "vendor-intake", "label": "Vendor intake", "status": "VALID" if phase != "CREATED" else "PENDING", "kind": "work"},
                {"id": "vendor-profile-r7", "label": "Profile r7", "status": "VALID", "kind": "artifact"},
                {"id": "soc2-A31", "label": "SOC2 A31", "status": "VALID", "kind": "evidence"},
            ],
        },
        {
            "agent_id": "security-agent",
            "label": "SECURITY AGENT",
            "status": _agent_status(snapshot, "security-agent"),
            "checkpoints": [
                {"id": "D42", "label": "Security decision", "status": decision["D42"].status.value, "kind": "decision"},
                *(
                    [{"id": open_commitment.commitment_id, "label": "Pen test required", "status": "WAITING", "kind": "commitment"}]
                    if open_commitment is not None and open_commitment.event_type == "vendor.document.uploaded"
                    else []
                ),
                *(
                    [{"id": "D57", "label": "Security revalidated", "status": decision["D57"].status.value, "kind": "decision"}]
                    if "D57" in decision else []
                ),
            ],
        },
        {
            "agent_id": "procurement-agent",
            "label": "PROCUREMENT AGENT",
            "status": _agent_status(snapshot, "procurement-agent"),
            "checkpoints": [
                {"id": "D43", "label": "Financial review", "status": decision["D43"].status.value, "kind": "decision", "preserved": phase in {"POLICY_DRIFT", "MISSING_EVIDENCE", "COMPLETED"}},
                {"id": "D50", "label": "Procurement decision", "status": decision["D50"].status.value, "kind": "decision"},
                *(
                    [{"id": "D58", "label": "Procurement resumed", "status": decision["D58"].status.value, "kind": "decision"}]
                    if "D58" in decision else []
                ),
                {"id": "activate-vendor", "label": "Vendor active", "status": "COMMITTED" if world.vendor.status is VendorStatus.ACTIVE else snapshot.graph.actions["activate-vendor"].status.value, "kind": "action"},
            ],
        },
    ]
    return {
        "mission": snapshot.mission.model_dump(mode="json"),
        "subject": {"id": world.vendor.vendor_id, "name": world.vendor.name},
        "scenario_phase": phase,
        "next_action": next_action,
        "execution_mode": world.execution_mode.value,
        "current_policy": world.artifacts[world.current_policy_id].version,
        "vendor_status": world.vendor.status.value,
        "agent_lanes": lanes,
        "commitments": [item.model_dump(mode="json") for item in snapshot.commitments],
        "side_effects": [item.model_dump(mode="json") for item in snapshot.side_effects],
        "timeline": [
            item.model_dump(mode="json")
            for item in sorted(snapshot.audit_events, key=lambda event: event.event_sequence, reverse=True)
        ],
        "graph": graph,
    }


def _phase(snapshot: RuntimeSnapshot) -> tuple[str, str]:
    if snapshot.mission.status is MissionStatus.CREATED:
        return "CREATED", "START"
    if snapshot.mission.status is MissionStatus.COMPLETED:
        return "COMPLETED", "RESET"
    if any(
        item.status is CommitmentStatus.OPEN
        and item.event_type == "vendor.document.uploaded"
        for item in snapshot.commitments
    ):
        return "MISSING_EVIDENCE", "UPLOAD_PEN_TEST"
    if snapshot.mission.status is MissionStatus.REVALIDATING:
        return "POLICY_DRIFT", "RUN_REVALIDATION"
    return "BASELINE_WAITING", "INJECT_POLICY"


def _agent_status(snapshot: RuntimeSnapshot, agent_id: str) -> str:
    items = [item for item in snapshot.work_items if item.target_agent == agent_id]
    if not items:
        return "PENDING"
    priority = {"RUNNING": 5, "WAITING": 4, "PENDING": 3, "DISPATCHED": 2, "SUCCEEDED": 1, "CANCELLED": 0, "FAILED": 6}
    return max(items, key=lambda item: priority[item.status.value]).status.value


def _plan(graph: GraphSnapshot) -> RevalidationPlan:
    repository = InMemoryGraphRepository()
    repository.create_snapshot(graph)
    return RevalidationService(repository).plan(graph.mission_id)
