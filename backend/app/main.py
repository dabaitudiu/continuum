import os
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.agents.service import GoogleAdkMissionAgentService
from app.api.compiler_demo_routes import (
    CompilerEvidenceService,
    build_compiler_demo_router,
)
from app.api.compiler_routes import build_compiler_router
from app.api.read_models import graph_read_model
from app.api.runtime_routes import build_runtime_router
from app.compiler.acceptance import RuntimeAcceptanceService
from app.compiler.canonicalization import DeterministicCanonicalizer
from app.compiler.repository import CompilerRepository
from app.compiler.repository_firestore import FirestoreCompilerRepository
from app.compiler.repository_memory import InMemoryCompilerRepository
from app.compiler.repository_sqlite import SQLiteCompilerRepository
from app.compiler.review import AuthorityPrecedencePolicy, DeterministicReviewGate
from app.compiler.service import CompilerService
from app.compiler.validation import DeterministicDraftValidator
from app.demo.compiler_fixture import (
    CompilerReferenceCatalog,
    ReferenceAwareCompletenessCritic,
    build_reference_catalog,
)
from app.demo.fixture import seed_canonical_mission
from app.domain.invalidation import InvalidationService
from app.domain.models import (
    DomainEvent,
)
from app.domain.revalidation import RevalidationService
from app.events.outbox import GooglePubSubOutboxPublisher, OutboxRelay
from app.observability.telemetry import configure_telemetry
from app.repository.graph_adapter import RuntimeGraphRepositoryAdapter
from app.repository.protocol import GraphRepository
from app.repository.runtime_firestore import FirestoreRuntimeRepository
from app.repository.runtime_memory import InMemoryRuntimeRepository
from app.repository.runtime_protocol import RuntimeRepository
from app.repository.runtime_publishing import PublishingRuntimeRepository
from app.repository.runtime_sqlite import SQLiteRuntimeRepository
from app.runtime.coordinator import RuntimeCoordinator
from app.runtime.errors import RuntimeDomainError
from app.sources.registry import SourceRegistry


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
    compiler_repository: CompilerRepository | None = None,
    compiler_service: CompilerService | None = None,
    compiler_source_registry: SourceRegistry | None = None,
    runtime_compiler_acceptor: Any | None = None,
    runtime_compiler_capability: str | None = None,
    compiler_api_capability: str | None = None,
    compiler_budget_path: Path | None = None,
    compiler_evidence_report_path: Path | None = None,
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
    compiler_repo = compiler_repository or _default_compiler_repository(
        isolated=repository is not None or runtime_repository is not None
    )
    reference_catalog = build_reference_catalog()
    semantic_compiler = compiler_service or _default_compiler_service(reference_catalog)
    source_registry = compiler_source_registry or reference_catalog.registry
    compiler_acceptor = runtime_compiler_acceptor or RuntimeAcceptanceService(
        compiler_repo,
        runtime_repo,
    )
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
    app.include_router(
        build_compiler_router(
            repository=compiler_repo,
            compiler=semantic_compiler,
            source_registry=source_registry,
            runtime_acceptor=compiler_acceptor,
            runtime_capability=(
                runtime_compiler_capability
                if runtime_compiler_capability is not None
                else os.environ.get("CONTINUUM_RUNTIME_COMPILER_CAPABILITY")
            ),
            compiler_api_capability=(
                compiler_api_capability
                if compiler_api_capability is not None
                else os.environ.get("CONTINUUM_COMPILER_API_CAPABILITY")
            ),
        )
    )
    app.include_router(
        build_compiler_demo_router(
            repository=compiler_repo,
            compiler=semantic_compiler,
            catalog=reference_catalog,
            runtime_repository=runtime_repo,
            runtime_acceptor=compiler_acceptor,
            evidence=CompilerEvidenceService(
                report_path=(
                    compiler_evidence_report_path
                    or Path(__file__).resolve().parents[2]
                    / "docs"
                    / "reports"
                    / "module-01-dependency-compiler.json"
                ),
                budget_path=(
                    compiler_budget_path
                    or Path(
                        os.environ.get(
                            "CONTINUUM_OPENAI_BUDGET_LEDGER",
                            Path(__file__).resolve().parents[1]
                            / "data"
                            / "openai-benchmark-budget.db",
                        )
                    )
                ),
            ),
        )
    )

    @app.get("/api/health")
    def health() -> dict[str, str]:
        return {
            "status": "ok",
            "runtime": "continuum",
            "agent_mode": ("google_adk" if agent_reasoner is not None else "local"),
            "runtime_store": str(getattr(runtime_repo, "store_kind", "unknown")),
            "compiler_store": str(getattr(compiler_repo, "store_kind", "unknown")),
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
            return graph_read_model(
                result.snapshot.graph, revalidation.plan(request.mission_id)
            )
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
            return graph_read_model(
                result.snapshot.graph, revalidation.plan(mission_id)
            )
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
        repository: RuntimeRepository = FirestoreRuntimeRepository.from_environment(
            project=project,
            database=os.environ.get("CONTINUUM_FIRESTORE_DATABASE"),
            collection=os.environ.get(
                "CONTINUUM_FIRESTORE_COLLECTION",
                "missions",
            ),
        )
    elif store == "sqlite":
        configured_path = os.environ.get("CONTINUUM_DB_PATH")
        path = (
            Path(configured_path)
            if configured_path
            else Path(__file__).resolve().parents[1] / "data" / "continuum.db"
        )
        repository = SQLiteRuntimeRepository(path)
    else:
        raise RuntimeError("CONTINUUM_RUNTIME_STORE must be either sqlite or firestore")

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


def _default_compiler_service(
    reference_catalog: CompilerReferenceCatalog,
) -> CompilerService:
    return CompilerService(
        validator=DeterministicDraftValidator(),
        reviewer=DeterministicReviewGate(
            critic=ReferenceAwareCompletenessCritic(reference_catalog),
            precedence_policy=AuthorityPrecedencePolicy(),
        ),
        canonicalizer=DeterministicCanonicalizer(
            compiler_version="sdc-1",
            validation_policy_version="validation-v1",
        ),
        compiler_version="sdc-1",
        validation_policy_version="validation-v1",
    )


def _default_compiler_repository(*, isolated: bool) -> CompilerRepository:
    if isolated:
        return InMemoryCompilerRepository()
    store = os.environ.get(
        "CONTINUUM_COMPILER_STORE",
        os.environ.get("CONTINUUM_RUNTIME_STORE", "sqlite"),
    ).lower()
    if store == "firestore":
        project = os.environ.get("GOOGLE_CLOUD_PROJECT") or os.environ.get(
            "GCLOUD_PROJECT"
        )
        if not project:
            raise RuntimeError(
                "GOOGLE_CLOUD_PROJECT is required when "
                "CONTINUUM_COMPILER_STORE=firestore"
            )
        return FirestoreCompilerRepository.from_environment(
            project=project,
            database=os.environ.get("CONTINUUM_FIRESTORE_DATABASE"),
            collection=os.environ.get(
                "CONTINUUM_FIRESTORE_COMPILER_COLLECTION",
                "compiler_requests",
            ),
        )
    if store == "sqlite":
        configured_path = os.environ.get("CONTINUUM_DB_PATH")
        path = (
            Path(configured_path)
            if configured_path
            else Path(__file__).resolve().parents[1] / "data" / "continuum.db"
        )
        return SQLiteCompilerRepository(path)
    raise RuntimeError("CONTINUUM_COMPILER_STORE must be either sqlite or firestore")


def _http_error(status_code: int, code: str, message: str) -> HTTPException:
    return HTTPException(
        status_code=status_code,
        detail={"code": code, "message": message},
    )


app = create_app()
