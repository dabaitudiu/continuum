from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from app.demo.fixture import seed_canonical_mission
from app.domain.invalidation import InvalidationService
from app.domain.models import (
    ActionStatus,
    DecisionStatus,
    DomainEvent,
    GraphSnapshot,
    RevalidationPlan,
)
from app.domain.revalidation import RevalidationService
from app.repository.memory import InMemoryGraphRepository
from app.repository.protocol import GraphRepository


class PolicyUpgradeRequest(BaseModel):
    mission_id: str
    event_id: str


class RevalidationRequest(BaseModel):
    request_id: str


def create_app(repository: GraphRepository | None = None) -> FastAPI:
    repo = repository or InMemoryGraphRepository()
    app = FastAPI(title="Continuum Falsification Gate")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
        allow_credentials=False,
        allow_methods=["GET", "POST"],
        allow_headers=["Content-Type"],
    )

    invalidation = InvalidationService(repo)
    revalidation = RevalidationService(repo)

    @app.post("/api/demo/reset")
    def reset_demo() -> dict[str, str]:
        return {"mission_id": seed_canonical_mission(repo)}

    @app.post("/api/demo/policy/upgrade")
    def upgrade_policy(request: PolicyUpgradeRequest) -> dict[str, Any]:
        event = DomainEvent(
            event_id=request.event_id,
            event_type="policy.version.changed",
            payload={
                "logical_key": "security-policy",
                "old_artifact_id": "policy-v12",
                "new_artifact_id": "policy-v13",
                "old_version": "v12",
                "new_version": "v13",
            },
        )
        try:
            snapshot = invalidation.process_artifact_change(
                request.mission_id,
                event,
            )
        except KeyError as error:
            raise _http_error(404, "MISSION_NOT_FOUND", str(error)) from error
        except ValueError as error:
            raise _http_error(
                409,
                "POLICY_VERSION_CONFLICT",
                str(error),
            ) from error
        return _graph_read_model(snapshot, revalidation.plan(request.mission_id))

    @app.get("/api/missions/{mission_id}/graph")
    def get_graph(mission_id: str) -> dict[str, Any]:
        try:
            snapshot = repo.get_snapshot(mission_id)
            plan = revalidation.plan(mission_id)
        except KeyError as error:
            raise _http_error(404, "MISSION_NOT_FOUND", str(error)) from error
        return _graph_read_model(snapshot, plan)

    @app.post("/api/missions/{mission_id}/revalidate")
    def dispatch_revalidation(
        mission_id: str,
        request: RevalidationRequest,
    ) -> dict[str, Any]:
        try:
            plan = revalidation.plan(mission_id)
            already_processed = repo.has_processed_request(
                mission_id,
                request.request_id,
            )
            if not plan.runnable_decision_ids and not already_processed:
                raise _http_error(
                    409,
                    "REVALIDATION_NOT_AVAILABLE",
                    "no stale decision is currently runnable",
                )
            revalidation.dispatch(mission_id, request.request_id)
            snapshot = repo.get_snapshot(mission_id)
            return _graph_read_model(snapshot, revalidation.plan(mission_id))
        except HTTPException:
            raise
        except KeyError as error:
            raise _http_error(404, "MISSION_NOT_FOUND", str(error)) from error

    return app


def _http_error(status_code: int, code: str, message: str) -> HTTPException:
    return HTTPException(
        status_code=status_code,
        detail={"code": code, "message": message},
    )


def _graph_read_model(
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


app = create_app()
