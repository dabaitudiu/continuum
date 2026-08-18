import os
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException
from pydantic import BaseModel

from app.api.runtime_routes import build_runtime_router
from app.api.read_models import graph_read_model
from app.agents.service import GoogleAdkMissionAgentService
from app.demo.fixture import seed_canonical_mission
from app.events.outbox import GooglePubSubOutboxPublisher, OutboxRelay
from app.observability.telemetry import configure_telemetry
from app.domain.invalidation import InvalidationService
from app.domain.models import (
    ActionStatus,
    DecisionStatus,
    DomainEvent,
    GraphSnapshot,
    RevalidationPlan,
)
from app.domain.revalidation import RevalidationService
from app.repository.graph_adapter import RuntimeGraphRepositoryAdapter
from app.repository.protocol import GraphRepository
from app.repository.runtime_firestore import FirestoreRuntimeRepository
from app.repository.runtime_memory import InMemoryRuntimeRepository
from app.repository.runtime_publishing import PublishingRuntimeRepository
from app.repository.runtime_protocol import RuntimeRepository
from app.repository.runtime_sqlite import SQLiteRuntimeRepository
from app.runtime.coordinator import RuntimeCoordinator
from app.runtime.errors import RuntimeDomainError


class PolicyUpgradeRequest(BaseModel):
    mission_id: str
    event_id: str


class RevalidationRequest(BaseModel):
    request_id: str


class PenTestUploadRequest(BaseModel):
    mission_id: str
    event_id: str


def create_app(
    repository: GraphRepository | None = None,
    *,
    runtime_repository: RuntimeRepository | None = None,
    static_dir: Path | None = None,
) -> FastAPI:
    runtime_repo = runtime_repository or _default_runtime_repository(
        isolated=repository is not None
    )
    repo = repository or RuntimeGraphRepositoryAdapter(runtime_repo)
    agent_reasoner = (
        GoogleAdkMissionAgentService.from_environment()
        if os.environ.get("CONTINUUM_AGENT_MODE") == "google_adk"
        else None
    )
    coordinator = RuntimeCoordinator(runtime_repo, agent_reasoner)
    app = FastAPI(title="Continuum")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
        allow_credentials=False,
        allow_methods=["GET", "POST"],
        allow_headers=["Content-Type"],
    )
    telemetry_exporter = configure_telemetry(app)

    invalidation = InvalidationService(repo)
    revalidation = RevalidationService(repo)

    @app.exception_handler(RuntimeDomainError)
    async def runtime_error_handler(
        _request: Request,
        error: RuntimeDomainError,
    ) -> JSONResponse:
        if error.code == "MISSION_NOT_FOUND":
            status_code = 404
        elif error.code == "EVENT_SCHEMA_INVALID":
            status_code = 422
        else:
            status_code = 409
        return JSONResponse(
            status_code=status_code,
            content={
                "detail": {
                    "code": error.code,
                    "message": error.message,
                }
            },
        )

    app.include_router(build_runtime_router(coordinator))

    @app.get("/api/health")
    def health() -> dict[str, str]:
        return {
            "status": "ok",
            "runtime": "continuum",
            "agent_mode": (
                "google_adk" if agent_reasoner is not None else "local"
            ),
            "runtime_store": str(
                getattr(runtime_repo, "store_kind", "unknown")
            ),
            "event_transport": (
                "pubsub"
                if isinstance(runtime_repo, PublishingRuntimeRepository)
                else "local_outbox"
            ),
            "telemetry_exporter": telemetry_exporter,
        }

    @app.post("/api/demo/reset")
    def reset_demo() -> dict[str, str]:
        return {"mission_id": seed_canonical_mission(repo)}

    @app.post("/api/demo/policy/upgrade")
    def upgrade_policy(request: PolicyUpgradeRequest) -> dict[str, Any]:
        try:
            runtime_snapshot = coordinator.get(request.mission_id)
        except RuntimeDomainError as error:
            if error.code != "MISSION_NOT_FOUND":
                raise
            runtime_snapshot = None
        if runtime_snapshot is not None and runtime_snapshot.world is not None:
            result = coordinator.upgrade_policy(request.mission_id, request.event_id)
            return graph_read_model(result.snapshot.graph, revalidation.plan(request.mission_id))
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
        return graph_read_model(snapshot, revalidation.plan(request.mission_id))

    @app.post("/api/demo/documents/pen-test")
    def upload_pen_test(request: PenTestUploadRequest) -> dict[str, Any]:
        result = coordinator.upload_pen_test(request.mission_id, request.event_id)
        return {
            **result.result,
            "duplicate": result.duplicate,
        }

    @app.get("/api/missions/{mission_id}/graph")
    def get_graph(mission_id: str) -> dict[str, Any]:
        try:
            snapshot = repo.get_snapshot(mission_id)
            plan = revalidation.plan(mission_id)
        except KeyError as error:
            raise _http_error(404, "MISSION_NOT_FOUND", str(error)) from error
        return graph_read_model(snapshot, plan)

    @app.post("/api/missions/{mission_id}/revalidate")
    def dispatch_revalidation(
        mission_id: str,
        request: RevalidationRequest,
    ) -> dict[str, Any]:
        try:
            runtime_snapshot = coordinator.get(mission_id)
        except RuntimeDomainError as error:
            if error.code != "MISSION_NOT_FOUND":
                raise
            runtime_snapshot = None
        if runtime_snapshot is not None and runtime_snapshot.world is not None:
            result = coordinator.revalidate_affected_branch(
                mission_id,
                request.request_id,
            )
            return graph_read_model(result.snapshot.graph, revalidation.plan(mission_id))
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
            return graph_read_model(snapshot, revalidation.plan(mission_id))
        except HTTPException:
            raise
        except KeyError as error:
            raise _http_error(404, "MISSION_NOT_FOUND", str(error)) from error

    resolved_static = static_dir or _configured_static_dir()
    if resolved_static is not None and resolved_static.is_dir():
        app.mount("/", SpaStaticFiles(directory=resolved_static, html=True))

    return app


class SpaStaticFiles(StaticFiles):
    async def get_response(self, path: str, scope):  # type: ignore[no-untyped-def]
        try:
            response = await super().get_response(path, scope)
        except StarletteHTTPException as error:
            if error.status_code == 404 and "." not in Path(path).name:
                return await super().get_response("index.html", scope)
            raise
        if response.status_code == 404 and "." not in Path(path).name:
            return await super().get_response("index.html", scope)
        return response


def _configured_static_dir() -> Path | None:
    configured = os.environ.get("CONTINUUM_STATIC_DIR")
    if configured:
        return Path(configured)
    bundled = Path(__file__).resolve().parents[1] / "static"
    return bundled if bundled.is_dir() else None


def _default_runtime_repository(*, isolated: bool) -> RuntimeRepository:
    if isolated:
        return InMemoryRuntimeRepository()
    store = os.environ.get("CONTINUUM_RUNTIME_STORE", "sqlite").lower()
    if store == "firestore":
        project = os.environ.get("GOOGLE_CLOUD_PROJECT") or os.environ.get(
            "GCLOUD_PROJECT"
        )
        if not project:
            raise RuntimeError(
                "GOOGLE_CLOUD_PROJECT is required when "
                "CONTINUUM_RUNTIME_STORE=firestore"
            )
        repository: RuntimeRepository = (
            FirestoreRuntimeRepository.from_environment(
                project=project,
                database=os.environ.get("CONTINUUM_FIRESTORE_DATABASE"),
                collection=os.environ.get(
                    "CONTINUUM_FIRESTORE_COLLECTION",
                    "missions",
                ),
            )
        )
    elif store == "sqlite":
        configured_path = os.environ.get("CONTINUUM_DB_PATH")
        path = (
            Path(configured_path)
            if configured_path
            else Path(__file__).resolve().parents[1]
            / "data"
            / "continuum.db"
        )
        repository = SQLiteRuntimeRepository(path)
    else:
        raise RuntimeError(
            "CONTINUUM_RUNTIME_STORE must be either sqlite or firestore"
        )

    topic = os.environ.get("CONTINUUM_PUBSUB_TOPIC")
    if topic:
        project = os.environ.get("GOOGLE_CLOUD_PROJECT") or os.environ.get(
            "GCLOUD_PROJECT"
        )
        if not project:
            raise RuntimeError(
                "GOOGLE_CLOUD_PROJECT is required when "
                "CONTINUUM_PUBSUB_TOPIC is configured"
            )
        publisher = GooglePubSubOutboxPublisher.from_environment(
            project=project,
            topic=topic,
        )
        return PublishingRuntimeRepository(
            repository,
            OutboxRelay(repository, publisher),
        )
    return repository


def _http_error(status_code: int, code: str, message: str) -> HTTPException:
    return HTTPException(
        status_code=status_code,
        detail={"code": code, "message": message},
    )


app = create_app()
