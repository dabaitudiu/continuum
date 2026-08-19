from __future__ import annotations

import json
import os
from decimal import Decimal
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict, Field

from app.compiler.acceptance import CompilerAcceptanceError
from app.compiler.budget import SQLiteBudgetLedger
from app.compiler.context import CompilationContext, RiskClass
from app.compiler.reasoner import openai_luna_pricing
from app.compiler.repository import (
    CompilationAggregate,
    CompilationRequestRecord,
    CompilerRepository,
    CompilerRepositoryError,
)
from app.compiler.service import CompilerService
from app.demo.compiler_fixture import (
    REFERENCE_NOW,
    REFERENCE_SCOPE,
    REFERENCE_WORLD_SNAPSHOT,
    CompilerReferenceCatalog,
    ReferenceScenarioSummary,
    ReferenceSourceView,
    ensure_reference_runtime,
    reference_mission_id,
    reference_request_id,
    reference_scenario_id,
)
from app.repository.runtime_protocol import RuntimeRepository
from app.runtime.errors import RuntimeDomainError


class FrozenModel(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class ReferenceRunRequest(FrozenModel):
    request_id: str = Field(min_length=1, max_length=256)


class BudgetEvidence(FrozenModel):
    limit_usd: str
    spent_usd: str
    reserved_usd: str
    remaining_usd: str
    settled_calls: int
    reserved_calls: int
    pricing_version: str


class ProviderEvidence(FrozenModel):
    status: str
    provider: str
    model: str
    reason: str | None = None
    credentials_configured: bool
    report_run_id: str | None = None
    budget: BudgetEvidence | None = None


class CompilerEvidence(FrozenModel):
    deterministic_reference: ProviderEvidence
    openai: ProviderEvidence
    gemini: ProviderEvidence


class CompilerLabStatus(FrozenModel):
    execution_mode: str = "DETERMINISTIC_REFERENCE"
    scenarios: list[ReferenceScenarioSummary]
    evidence: CompilerEvidence


class RuntimeReceipt(FrozenModel):
    duplicate: bool
    mission_id: str
    mission_revision: int
    decision_id: str
    claim_ids: list[str]
    evidence_ids: list[str]
    compilation_id: str
    compilation_hash: str
    audit_event_id: str
    audit_link: str


class CompilerLabView(FrozenModel):
    scenario_id: str
    scenario_label: str
    scenario_summary: str
    execution_mode: str = "DETERMINISTIC_REFERENCE"
    aggregate: CompilationAggregate
    sources: list[ReferenceSourceView]
    evidence: CompilerEvidence
    runtime_receipt: RuntimeReceipt | None = None


class CompilerEvidenceService:
    def __init__(self, *, report_path: Path, budget_path: Path) -> None:
        self._report_path = report_path
        self._budget_path = budget_path

    def status(self) -> CompilerEvidence:
        runs = self._report_runs()
        openai_run = _latest_lane(runs, "live_openai")
        gemini_run = _latest_lane(runs, "live_gemini")
        openai_credentials = bool(os.environ.get("OPENAI_API_KEY"))
        gemini_credentials = bool(
            os.environ.get("GEMINI_API_KEY")
            or os.environ.get("GOOGLE_API_KEY")
            or (
                os.environ.get("GOOGLE_GENAI_USE_VERTEXAI", "").upper() == "TRUE"
                and os.environ.get("GOOGLE_CLOUD_PROJECT")
                and os.environ.get("GOOGLE_CLOUD_LOCATION")
            )
        )
        pricing = openai_luna_pricing()
        ledger = SQLiteBudgetLedger(self._budget_path, limit_usd=Decimal(10))
        try:
            budget = ledger.snapshot()
        finally:
            ledger.close()
        return CompilerEvidence(
            deterministic_reference=ProviderEvidence(
                status="PASS",
                provider="REFERENCE",
                model="deterministic-reference-v1",
                reason="Repeatable product fixture; not live model evidence.",
                credentials_configured=True,
            ),
            openai=_provider_evidence(
                provider="OPENAI",
                default_model=os.environ.get(
                    "CONTINUUM_OPENAI_MODEL",
                    pricing.model_name,
                ),
                credentials_configured=openai_credentials,
                missing_reason="OPENAI_API_KEY is not configured",
                run=openai_run,
                budget=BudgetEvidence(
                    limit_usd=str(budget.limit_usd),
                    spent_usd=str(budget.spent_usd),
                    reserved_usd=str(budget.reserved_usd),
                    remaining_usd=str(budget.remaining_usd),
                    settled_calls=budget.settled_calls,
                    reserved_calls=budget.reserved_calls,
                    pricing_version=pricing.pricing_version,
                ),
            ),
            gemini=_provider_evidence(
                provider="GOOGLE",
                default_model=os.environ.get(
                    "CONTINUUM_GEMINI_MODEL",
                    "gemini-3.5-flash",
                ),
                credentials_configured=gemini_credentials,
                missing_reason=(
                    "Gemini API key or configured Vertex credentials are not configured"
                ),
                run=gemini_run,
            ),
        )

    def _report_runs(self) -> list[dict[str, Any]]:
        if not self._report_path.exists():
            return []
        try:
            payload = json.loads(self._report_path.read_text(encoding="utf-8"))
        except (OSError, ValueError, TypeError):
            return []
        runs = payload.get("runs", [])
        return [run for run in runs if isinstance(run, dict)]


def build_compiler_demo_router(
    *,
    repository: CompilerRepository,
    compiler: CompilerService,
    catalog: CompilerReferenceCatalog,
    runtime_repository: RuntimeRepository,
    runtime_acceptor: Any,
    evidence: CompilerEvidenceService,
) -> APIRouter:
    router = APIRouter(prefix="/api/demo/compiler", tags=["compiler-demo"])

    @router.get("/status", response_model=CompilerLabStatus)
    def get_status() -> CompilerLabStatus:
        return CompilerLabStatus(
            scenarios=[
                catalog.scenarios[scenario_id].summary
                for scenario_id in sorted(catalog.scenarios)
            ],
            evidence=evidence.status(),
        )

    @router.post(
        "/scenarios/{scenario_id}",
        response_model=CompilerLabView,
    )
    def run_scenario(
        scenario_id: str,
        payload: ReferenceRunRequest,
    ) -> CompilerLabView:
        try:
            scenario = catalog.scenario(scenario_id)
        except KeyError as error:
            raise HTTPException(
                status_code=404,
                detail={
                    "code": "REFERENCE_SCENARIO_NOT_FOUND",
                    "message": str(error),
                },
            ) from error
        request_id = reference_request_id(scenario_id, payload.request_id)
        runtime = ensure_reference_runtime(
            runtime_repository,
            request_id=request_id,
        )
        expected_request = CompilationRequestRecord(
            request_id=request_id,
            mission_id=runtime.mission.mission_id,
            work_item_id=f"{runtime.mission.mission_id}:compile-access",
            agent_id="reference-compiler-adapter",
            world_snapshot_id=REFERENCE_WORLD_SNAPSHOT,
            expected_mission_revision=0,
            decision_type="PRIVILEGED_ACCESS_REVIEW",
            risk_class=RiskClass.HIGH,
            owner_scope=REFERENCE_SCOPE,
            allowed_source_refs=list(scenario.allowed_source_refs),
            created_at=REFERENCE_NOW,
        )
        try:
            aggregate = repository.create_request(expected_request)
            aggregate = repository.put_draft(
                request_id,
                catalog.draft(scenario_id, request_id),
            )
            context = CompilationContext(
                source_registry=catalog.registry,
                world_snapshot_id=REFERENCE_WORLD_SNAPSHOT,
                owner_scope=REFERENCE_SCOPE,
                allowed_source_refs=frozenset(scenario.allowed_source_refs),
                risk_class=RiskClass.HIGH,
                decision_context={
                    "mission_id": runtime.mission.mission_id,
                    "work_item_id": f"{runtime.mission.mission_id}:compile-access",
                },
            )
            catalog.register(request_id)
            try:
                aggregate = repository.put_result(
                    request_id,
                    compiler.compile(aggregate.draft, context),  # type: ignore[arg-type]
                )
            except Exception:
                catalog.unregister(request_id)
                raise
        except CompilerRepositoryError as error:
            raise _repository_http_error(error) from error
        return _view(
            aggregate,
            catalog=catalog,
            runtime_repository=runtime_repository,
            evidence=evidence.status(),
        )

    @router.get("/{request_id}", response_model=CompilerLabView)
    def get_scenario(request_id: str) -> CompilerLabView:
        scenario_id = _require_reference_request(request_id, catalog)
        try:
            aggregate = repository.get(request_id)
        except CompilerRepositoryError as error:
            raise _repository_http_error(error) from error
        if aggregate.request.mission_id != reference_mission_id(request_id):
            raise _reference_fixture_required()
        return _view(
            aggregate,
            catalog=catalog,
            runtime_repository=runtime_repository,
            evidence=evidence.status(),
            scenario_id=scenario_id,
        )

    @router.post("/{request_id}/accept", response_model=CompilerLabView)
    def accept_scenario(request_id: str) -> CompilerLabView:
        scenario_id = _require_reference_request(request_id, catalog)
        if not catalog.is_registered(request_id):
            raise _reference_fixture_required()
        try:
            aggregate = repository.get(request_id)
        except CompilerRepositoryError as error:
            raise _repository_http_error(error) from error
        if aggregate.request.mission_id != reference_mission_id(request_id):
            raise _reference_fixture_required()
        try:
            accepted = runtime_acceptor.accept(
                request_id,
                expected_mission_revision=aggregate.request.expected_mission_revision,
                world_snapshot_id=aggregate.request.world_snapshot_id,
            )
        except CompilerAcceptanceError as error:
            raise HTTPException(
                status_code=409,
                detail={"code": error.code, "message": error.message},
            ) from error
        except CompilerRepositoryError as error:
            raise _repository_http_error(error) from error
        return _view(
            aggregate,
            catalog=catalog,
            runtime_repository=runtime_repository,
            evidence=evidence.status(),
            scenario_id=scenario_id,
            duplicate=bool(accepted.duplicate),
        )

    return router


def _view(
    aggregate: CompilationAggregate,
    *,
    catalog: CompilerReferenceCatalog,
    runtime_repository: RuntimeRepository,
    evidence: CompilerEvidence,
    scenario_id: str | None = None,
    duplicate: bool | None = None,
) -> CompilerLabView:
    resolved_scenario_id = scenario_id or reference_scenario_id(
        aggregate.request.request_id
    )
    if resolved_scenario_id is None:
        raise _reference_fixture_required()
    scenario = catalog.scenario(resolved_scenario_id)
    receipt = _runtime_receipt(
        aggregate,
        runtime_repository=runtime_repository,
        duplicate=duplicate,
    )
    return CompilerLabView(
        scenario_id=resolved_scenario_id,
        scenario_label=scenario.summary.label,
        scenario_summary=scenario.summary.summary,
        aggregate=aggregate,
        sources=catalog.source_views(resolved_scenario_id),
        evidence=evidence,
        runtime_receipt=receipt,
    )


def _runtime_receipt(
    aggregate: CompilationAggregate,
    *,
    runtime_repository: RuntimeRepository,
    duplicate: bool | None,
) -> RuntimeReceipt | None:
    result = aggregate.result
    if result is None or result.compilation_hash is None:
        return None
    message_id = f"compiler-accept:{result.compilation_id}"
    try:
        inbox = runtime_repository.find_inbox(
            aggregate.request.mission_id,
            message_id,
        )
    except RuntimeDomainError as error:
        if error.code == "MISSION_NOT_FOUND":
            return None
        raise
    if inbox is None:
        return None
    snapshot = runtime_repository.load(aggregate.request.mission_id)
    audit = next(
        event
        for event in snapshot.audit_events
        if event.payload.get("compilation_id") == result.compilation_id
    )
    evidence_ids = sorted(
        {
            edge.source_id
            for edge in result.canonical_edges
            if edge.source_kind == "SOURCE_FRAGMENT"
        }
    )
    return RuntimeReceipt(
        duplicate=bool(duplicate),
        mission_id=aggregate.request.mission_id,
        mission_revision=snapshot.mission.revision,
        decision_id=inbox.result["decision_id"],
        claim_ids=sorted(claim.claim_id for claim in result.canonical_claims),
        evidence_ids=evidence_ids,
        compilation_id=result.compilation_id,
        compilation_hash=result.compilation_hash,
        audit_event_id=audit.audit_event_id,
        audit_link=f"/api/demo/compiler/{aggregate.request.request_id}",
    )


def _provider_evidence(
    *,
    provider: str,
    default_model: str,
    credentials_configured: bool,
    missing_reason: str,
    run: dict[str, Any] | None,
    budget: BudgetEvidence | None = None,
) -> ProviderEvidence:
    configuration = {} if run is None else run.get("configuration", {})
    report_status = None if run is None else run.get("status")
    report_passed = report_status == "PASS"
    status = "PASS" if report_passed else "BLOCKED"
    reason = (
        None
        if report_passed
        else (
            missing_reason
            if not credentials_configured
            else (None if run is None else run.get("blocked_reason"))
            or "No passing live evidence run is recorded for the current configuration"
        )
    )
    return ProviderEvidence(
        status=status,
        provider=provider,
        model=str(configuration.get("reasoner_model") or default_model),
        reason=reason,
        credentials_configured=credentials_configured,
        report_run_id=None if run is None else run.get("run_id"),
        budget=budget,
    )


def _latest_lane(
    runs: list[dict[str, Any]],
    lane: str,
) -> dict[str, Any] | None:
    matches = [
        run for run in runs if run.get("configuration", {}).get("evidence_lane") == lane
    ]
    return None if not matches else matches[-1]


def _require_reference_request(
    request_id: str,
    catalog: CompilerReferenceCatalog,
) -> str:
    scenario_id = reference_scenario_id(request_id)
    if scenario_id is None or scenario_id not in catalog.scenarios:
        raise _reference_fixture_required()
    return scenario_id


def _reference_fixture_required() -> HTTPException:
    return HTTPException(
        status_code=403,
        detail={
            "code": "REFERENCE_FIXTURE_REQUIRED",
            "message": "demo orchestration accepts only server-registered reference fixtures",
        },
    )


def _repository_http_error(error: CompilerRepositoryError) -> HTTPException:
    return HTTPException(
        status_code=(404 if error.code == "COMPILATION_REQUEST_NOT_FOUND" else 409),
        detail={"code": error.code, "message": error.message},
    )


__all__ = [
    "CompilerEvidenceService",
    "CompilerLabStatus",
    "CompilerLabView",
    "build_compiler_demo_router",
]
