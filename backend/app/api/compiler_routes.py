from __future__ import annotations

import secrets
from datetime import UTC, datetime
from typing import Any, Protocol

from fastapi import APIRouter, Header, HTTPException, status
from pydantic import BaseModel, Field

from app.compiler.context import CompilationContext, RiskClass
from app.compiler.acceptance import CompilerAcceptanceError
from app.compiler.models import DecisionDraft
from app.compiler.repository import (
    CompilationAggregate,
    CompilationRequestRecord,
    CompilationState,
    CompilerRepository,
    CompilerRepositoryError,
)
from app.compiler.service import CompilerService
from app.sources.registry import SourceRegistry


class CompilationRequestCreate(BaseModel):
    request_id: str = Field(min_length=1, max_length=256)
    mission_id: str = Field(min_length=1, max_length=256)
    work_item_id: str = Field(min_length=1, max_length=256)
    agent_id: str = Field(min_length=1, max_length=256)
    world_snapshot_id: str = Field(min_length=1, max_length=256)
    expected_mission_revision: int = Field(ge=0)
    decision_type: str = Field(min_length=1, max_length=128)
    risk_class: RiskClass
    owner_scope: str = Field(min_length=1, max_length=256)
    allowed_source_refs: list[str] = Field(min_length=1, max_length=500)
    allow_historical: bool = False


class RuntimeAcceptRequest(BaseModel):
    expected_mission_revision: int = Field(ge=0)
    world_snapshot_id: str = Field(min_length=1, max_length=256)


class RuntimeCompilationAcceptor(Protocol):
    def accept(
        self,
        request_id: str,
        *,
        expected_mission_revision: int,
        world_snapshot_id: str,
    ) -> Any: ...


def build_compiler_router(
    *,
    repository: CompilerRepository,
    compiler: CompilerService,
    source_registry: SourceRegistry,
    runtime_acceptor: RuntimeCompilationAcceptor | None = None,
    runtime_capability: str | None = None,
) -> APIRouter:
    router = APIRouter(prefix="/api/compiler", tags=["compiler"])

    @router.post(
        "/requests",
        response_model=CompilationAggregate,
        status_code=status.HTTP_201_CREATED,
    )
    def create_request(payload: CompilationRequestCreate) -> CompilationAggregate:
        try:
            return repository.create_request(
                CompilationRequestRecord(
                    **payload.model_dump(exclude={"allow_historical"}),
                    allow_historical=payload.allow_historical,
                    created_at=datetime.now(UTC),
                )
            )
        except CompilerRepositoryError as error:
            raise _repository_http_error(error) from error

    @router.post("/{request_id}/draft", response_model=CompilationAggregate)
    def put_draft(
        request_id: str,
        draft: DecisionDraft,
    ) -> CompilationAggregate:
        try:
            return repository.put_draft(request_id, draft)
        except CompilerRepositoryError as error:
            raise _repository_http_error(error) from error

    @router.post("/{request_id}/compile", response_model=CompilationAggregate)
    def compile_request(request_id: str) -> CompilationAggregate:
        try:
            aggregate = repository.get(request_id)
            if aggregate.result is not None:
                return aggregate
            if (
                aggregate.state is not CompilationState.DRAFT_RECEIVED
                or aggregate.draft is None
            ):
                raise CompilerRepositoryError(
                    "COMPILATION_STATE_CONFLICT",
                    f"request cannot compile from state {aggregate.state}",
                )
            request = aggregate.request
            context = CompilationContext(
                source_registry=source_registry,
                world_snapshot_id=request.world_snapshot_id,
                owner_scope=request.owner_scope,
                allowed_source_refs=frozenset(request.allowed_source_refs),
                risk_class=request.risk_class,
                allow_historical=request.allow_historical,
                decision_context={
                    "mission_id": request.mission_id,
                    "work_item_id": request.work_item_id,
                },
            )
            result = compiler.compile(aggregate.draft, context)
            return repository.put_result(request_id, result)
        except CompilerRepositoryError as error:
            raise _repository_http_error(error) from error

    @router.get("/{request_id}", response_model=CompilationAggregate)
    def get_request(request_id: str) -> CompilationAggregate:
        try:
            return repository.get(request_id)
        except CompilerRepositoryError as error:
            raise _repository_http_error(error) from error

    @router.post("/{request_id}/accept")
    def accept_request(
        request_id: str,
        payload: RuntimeAcceptRequest,
        x_continuum_runtime_capability: str | None = Header(default=None),
    ) -> Any:
        if (
            runtime_capability is None
            or x_continuum_runtime_capability is None
            or not secrets.compare_digest(
                runtime_capability,
                x_continuum_runtime_capability,
            )
        ):
            raise HTTPException(
                status_code=403,
                detail={
                    "code": "RUNTIME_CAPABILITY_REQUIRED",
                    "message": "runtime-only compiler acceptance capability is required",
                },
            )
        if runtime_acceptor is None:
            raise HTTPException(
                status_code=503,
                detail={
                    "code": "RUNTIME_ACCEPTOR_UNAVAILABLE",
                    "message": "runtime compiler acceptance is not configured",
                },
            )
        try:
            return runtime_acceptor.accept(
                request_id,
                expected_mission_revision=payload.expected_mission_revision,
                world_snapshot_id=payload.world_snapshot_id,
            )
        except CompilerRepositoryError as error:
            raise _repository_http_error(error) from error
        except CompilerAcceptanceError as error:
            raise HTTPException(
                status_code=409,
                detail={"code": error.code, "message": error.message},
            ) from error

    return router


def _repository_http_error(error: CompilerRepositoryError) -> HTTPException:
    status_code = (
        404 if error.code == "COMPILATION_REQUEST_NOT_FOUND" else 409
    )
    return HTTPException(
        status_code=status_code,
        detail={"code": error.code, "message": error.message},
    )
