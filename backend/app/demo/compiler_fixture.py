from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from datetime import UTC, datetime
from threading import RLock

from pydantic import BaseModel, ConfigDict

from app.compiler.context import CompilationContext
from app.compiler.models import (
    ClaimDraft,
    ClaimType,
    ContradictionProposal,
    CriticProposal,
    DecisionDraft,
    DependencyRef,
    DependencyRelation,
    Materiality,
    MissingDependencyProposal,
    ModelMetadata,
)
from app.compiler.prompts import REASONER_PROMPT_VERSION
from app.domain.models import GraphSnapshot
from app.repository.runtime_protocol import RuntimeRepository
from app.runtime.entities import (
    EnterpriseArtifact,
    EnterpriseWorld,
    Mission,
    RuntimeSnapshot,
    VendorRecord,
)
from app.runtime.errors import RuntimeDomainError
from app.sources.identity import (
    Artifact,
    ArtifactType,
    IngestedSource,
    SourceType,
    TrustClass,
    ingest_json_revision,
)
from app.sources.registry import InMemorySourceRegistry, WorldSnapshot

REFERENCE_REQUEST_PREFIX = "reference-compiler:"
REFERENCE_SCOPE = "tenant:continuum-reference"
REFERENCE_WORLD_SNAPSHOT = "world:compiler-reference:v13"
REFERENCE_NOW = datetime(2026, 8, 19, 4, 30, tzinfo=UTC)


class ReferenceSourceView(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    source_ref: str
    logical_key: str
    artifact_type: str
    source_type: str
    trust_class: str
    authority_rank: int
    revision_label: str
    source_hash: str
    fragment_hash: str
    logical_path: str
    content: object
    historical: bool


class ReferenceScenarioSummary(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    scenario_id: str
    label: str
    summary: str
    expected_disposition: str


@dataclass(frozen=True, slots=True)
class ReferenceScenario:
    summary: ReferenceScenarioSummary
    allowed_source_refs: tuple[str, ...]
    draft_claims: tuple[ClaimDraft, ...]
    critic_proposal: CriticProposal


@dataclass(frozen=True, slots=True)
class CompilerReferenceCatalog:
    registry: InMemorySourceRegistry
    scenarios: dict[str, ReferenceScenario]
    sources_by_ref: dict[str, ReferenceSourceView]
    _registered_requests: set[str] = field(default_factory=set, repr=False)
    _registration_lock: RLock = field(default_factory=RLock, repr=False)

    def scenario(self, scenario_id: str) -> ReferenceScenario:
        try:
            return self.scenarios[scenario_id]
        except KeyError as error:
            raise KeyError(
                f"unknown reference compiler scenario: {scenario_id}"
            ) from error

    def source_views(self, scenario_id: str) -> list[ReferenceSourceView]:
        scenario = self.scenario(scenario_id)
        return [
            self.sources_by_ref[source_ref]
            for source_ref in scenario.allowed_source_refs
        ]

    def draft(self, scenario_id: str, request_id: str) -> DecisionDraft:
        scenario = self.scenario(scenario_id)
        return DecisionDraft(
            request_id=request_id,
            decision_type="PRIVILEGED_ACCESS_REVIEW",
            proposed_outcome="APPROVED",
            claims=list(scenario.draft_claims),
            decision_dependencies=[],
            unresolved_questions=[],
            rationale_summary=(
                "The bounded source set was evaluated for privileged production access."
            ),
            model_metadata=ModelMetadata(
                provider="REFERENCE",
                model_name="deterministic-reference-v1",
                prompt_version=REASONER_PROMPT_VERSION,
                temperature=0.0,
                execution_id=f"{request_id}:reasoner:1",
            ),
        )

    def register(self, request_id: str) -> None:
        scenario_id = reference_scenario_id(request_id)
        if scenario_id is None or scenario_id not in self.scenarios:
            raise ValueError("only a known reference request can be registered")
        with self._registration_lock:
            self._registered_requests.add(request_id)

    def unregister(self, request_id: str) -> None:
        with self._registration_lock:
            self._registered_requests.discard(request_id)

    def is_registered(self, request_id: str) -> bool:
        with self._registration_lock:
            return request_id in self._registered_requests


class FailClosedCompletenessCritic:
    """Refuses to treat an absent completeness reviewer as positive evidence."""

    def review(
        self,
        draft: DecisionDraft,
        context: CompilationContext,
    ) -> CriticProposal:
        return CriticProposal(
            missing_dependencies=[
                MissingDependencyProposal(
                    candidate_ref="UNKNOWN_SOURCE_REQUIRED",
                    severity=Materiality.CRITICAL,
                    why=(
                        "No configured completeness critic can establish that all "
                        "critical dependencies were supplied."
                    ),
                )
            ]
        )


class ReferenceAwareCompletenessCritic:
    """Deterministic demo adapter; production requests still fail closed."""

    def __init__(self, catalog: CompilerReferenceCatalog) -> None:
        self._catalog = catalog
        self._fallback = FailClosedCompletenessCritic()

    def review(
        self,
        draft: DecisionDraft,
        context: CompilationContext,
    ) -> CriticProposal:
        scenario_id = reference_scenario_id(draft.request_id)
        if scenario_id is None or not self._catalog.is_registered(draft.request_id):
            return self._fallback.review(draft, context)
        try:
            return self._catalog.scenario(scenario_id).critic_proposal
        except KeyError:
            return self._fallback.review(draft, context)


def reference_request_id(scenario_id: str, client_request_id: str) -> str:
    digest = hashlib.sha256(client_request_id.encode("utf-8")).hexdigest()[:24]
    return f"{REFERENCE_REQUEST_PREFIX}{scenario_id}:{digest}"


def reference_scenario_id(request_id: str) -> str | None:
    if not request_id.startswith(REFERENCE_REQUEST_PREFIX):
        return None
    remainder = request_id.removeprefix(REFERENCE_REQUEST_PREFIX)
    scenario_id, separator, digest = remainder.partition(":")
    if not separator or not scenario_id or len(digest) != 24:
        return None
    return scenario_id


def reference_mission_id(request_id: str) -> str:
    digest = hashlib.sha256(request_id.encode("utf-8")).hexdigest()[:24]
    return f"compiler-reference-{digest}"


def ensure_reference_runtime(
    repository: RuntimeRepository,
    *,
    request_id: str,
) -> RuntimeSnapshot:
    mission_id = reference_mission_id(request_id)
    try:
        return repository.load(mission_id)
    except RuntimeDomainError as error:
        if error.code != "MISSION_NOT_FOUND":
            raise
    snapshot = RuntimeSnapshot(
        mission=Mission(
            mission_id=mission_id,
            mission_type="COMPILER_REFERENCE",
            subject_id="REFERENCE_ACCESS_REQUEST",
        ),
        graph=GraphSnapshot(
            mission_id=mission_id,
            metadata={"world_snapshot_id": REFERENCE_WORLD_SNAPSHOT},
        ),
        world=EnterpriseWorld(
            mission_id=mission_id,
            vendor=VendorRecord(
                vendor_id="REFERENCE_SUBJECT",
                name="Reference access subject",
                profile_revision="r18",
                handles_customer_pii=False,
            ),
            current_policy_id="policy:access",
            artifacts={
                "policy:access": EnterpriseArtifact(
                    artifact_id="policy:access",
                    artifact_type="POLICY",
                    version="v13",
                ),
                "record:employee": EnterpriseArtifact(
                    artifact_id="record:employee",
                    artifact_type="STRUCTURED_RECORD",
                    version="r18",
                ),
                "record:access-request": EnterpriseArtifact(
                    artifact_id="record:access-request",
                    artifact_type="STRUCTURED_RECORD",
                    version="r45",
                ),
            },
            world_snapshot_id=REFERENCE_WORLD_SNAPSHOT,
        ),
    )
    try:
        repository.create(snapshot)
    except RuntimeDomainError as error:
        if error.code != "MISSION_ALREADY_EXISTS":
            raise
    return repository.load(mission_id)


def build_reference_catalog() -> CompilerReferenceCatalog:
    registry = InMemorySourceRegistry()
    current: dict[str, IngestedSource] = {}
    all_sources: list[tuple[Artifact, IngestedSource]] = []

    access_policy = _artifact(
        "policy:access",
        logical_key="privileged-access-policy",
        artifact_type=ArtifactType.POLICY,
        source_type=SourceType.POLICY,
        authority_rank=100,
    )
    registry.add_artifact(access_policy)
    policy_v12 = _ingest(
        access_policy,
        "v12",
        {"rule": "Production access requires an active employee record."},
    )
    policy_v13 = _ingest(
        access_policy,
        "v13",
        {
            "rule": (
                "Privileged production access requires an active employee "
                "record and current manager approval."
            )
        },
    )
    _add_ingested(registry, policy_v12)
    _add_ingested(registry, policy_v13)
    current[access_policy.artifact_id] = policy_v13
    all_sources.extend(((access_policy, policy_v12), (access_policy, policy_v13)))

    employee = _artifact(
        "record:employee",
        logical_key="employee-directory-record",
        artifact_type=ArtifactType.RECORD,
        source_type=SourceType.STRUCTURED_RECORD,
        authority_rank=80,
    )
    request = _artifact(
        "record:access-request",
        logical_key="access-request-record",
        artifact_type=ArtifactType.RECORD,
        source_type=SourceType.STRUCTURED_RECORD,
        authority_rank=80,
    )
    regional = _artifact(
        "policy:regional-access",
        logical_key="regional-access-exception",
        artifact_type=ArtifactType.POLICY,
        source_type=SourceType.POLICY,
        authority_rank=90,
    )
    global_policy = _artifact(
        "policy:global-access",
        logical_key="global-access-control",
        artifact_type=ArtifactType.POLICY,
        source_type=SourceType.POLICY,
        authority_rank=90,
    )
    for artifact in (employee, request, regional, global_policy):
        registry.add_artifact(artifact)

    employee_r18 = _ingest(
        employee,
        "r18",
        {"status": "FTE / ACTIVE / ENGINEERING"},
    )
    request_r45 = _ingest(
        request,
        "r45",
        {"scope": "prod-db-read / PROJECT PHOENIX"},
    )
    regional_v3 = _ingest(
        regional,
        "v3",
        {"rule": "Regional exception permits the requested read scope."},
    )
    global_v3 = _ingest(
        global_policy,
        "v3",
        {"rule": "Global control prohibits regional production exceptions."},
    )
    for artifact, source in (
        (employee, employee_r18),
        (request, request_r45),
        (regional, regional_v3),
        (global_policy, global_v3),
    ):
        _add_ingested(registry, source)
        current[artifact.artifact_id] = source
        all_sources.append((artifact, source))

    registry.add_world_snapshot(
        WorldSnapshot(
            world_snapshot_id=REFERENCE_WORLD_SNAPSHOT,
            owner_scope=REFERENCE_SCOPE,
            current_revisions={
                artifact_id: source.revision.revision_id
                for artifact_id, source in current.items()
            },
            current_representations={
                source.revision.revision_id: source.representation.representation_id
                for source in current.values()
            },
            created_at=REFERENCE_NOW,
        )
    )

    sources_by_ref: dict[str, ReferenceSourceView] = {}
    for artifact, source in all_sources:
        fragment = source.fragments[0]
        source_ref = str(fragment.source_ref())
        sources_by_ref[source_ref] = ReferenceSourceView(
            source_ref=source_ref,
            logical_key=artifact.logical_key,
            artifact_type=artifact.artifact_type.value,
            source_type=artifact.source_type.value,
            trust_class=artifact.trust_class.value,
            authority_rank=artifact.authority_rank,
            revision_label=source.revision.revision_label,
            source_hash=source.revision.content_hash,
            fragment_hash=fragment.text_hash,
            logical_path=fragment.logical_path,
            content=source.fragment_values[fragment.logical_path],
            historical=(source is policy_v12),
        )

    policy_current_ref = str(policy_v13.fragments[0].source_ref())
    policy_old_ref = str(policy_v12.fragments[0].source_ref())
    employee_ref = str(employee_r18.fragments[0].source_ref())
    request_ref = str(request_r45.fragments[0].source_ref())
    regional_ref = str(regional_v3.fragments[0].source_ref())
    global_ref = str(global_v3.fragments[0].source_ref())

    accepted_claims = (
        _claim(
            "policy-rule",
            ClaimType.RULE,
            "Current policy requires active employment and manager approval.",
            policy_current_ref,
            DependencyRelation.GOVERNED_BY,
        ),
        _claim(
            "employee-status",
            ClaimType.FACT,
            "The requester has an active FTE engineering record.",
            employee_ref,
            DependencyRelation.SUPPORTED_BY,
        ),
        _claim(
            "request-scope",
            ClaimType.FACT,
            "The request is limited to production read access for Project Phoenix.",
            request_ref,
            DependencyRelation.SUPPORTED_BY,
        ),
    )
    scenarios = {
        "authorized-access": ReferenceScenario(
            summary=ReferenceScenarioSummary(
                scenario_id="authorized-access",
                label="Authorized access",
                summary="All critical source fragments are current and complete.",
                expected_disposition="ACCEPTED",
            ),
            allowed_source_refs=(policy_current_ref, employee_ref, request_ref),
            draft_claims=accepted_claims,
            critic_proposal=CriticProposal(),
        ),
        "missing-governing-clause": ReferenceScenario(
            summary=ReferenceScenarioSummary(
                scenario_id="missing-governing-clause",
                label="Missing governing clause",
                summary="The draft omits the current policy dependency.",
                expected_disposition="REJECTED_INCOMPLETE_DEPENDENCIES",
            ),
            allowed_source_refs=(policy_current_ref, employee_ref, request_ref),
            draft_claims=accepted_claims[1:],
            critic_proposal=CriticProposal(
                missing_dependencies=[
                    MissingDependencyProposal(
                        candidate_ref=policy_current_ref,
                        severity=Materiality.CRITICAL,
                        why=(
                            "The proposed approval omits the governing privileged "
                            "access policy clause."
                        ),
                    )
                ]
            ),
        ),
        "conflicting-authorities": ReferenceScenario(
            summary=ReferenceScenarioSummary(
                scenario_id="conflicting-authorities",
                label="Conflicting authorities",
                summary="Equal-rank policy sources materially disagree.",
                expected_disposition="NEEDS_HUMAN_REVIEW",
            ),
            allowed_source_refs=(regional_ref, global_ref, request_ref),
            draft_claims=(
                _claim(
                    "regional-rule",
                    ClaimType.RULE,
                    "The regional exception permits the requested production scope.",
                    regional_ref,
                    DependencyRelation.GOVERNED_BY,
                ),
                accepted_claims[2],
            ),
            critic_proposal=CriticProposal(
                possible_contradictions=[
                    ContradictionProposal(
                        claim_or_topic="regional production access exception",
                        source_ref_a=regional_ref,
                        source_ref_b=global_ref,
                        severity=Materiality.CRITICAL,
                        source_a_supports_outcome=True,
                        source_b_supports_outcome=False,
                    )
                ]
            ),
        ),
        "obsolete-policy-ref": ReferenceScenario(
            summary=ReferenceScenarioSummary(
                scenario_id="obsolete-policy-ref",
                label="Obsolete Policy v12 ref",
                summary="The draft cites a superseded business revision.",
                expected_disposition="REJECTED_STALE_SOURCE",
            ),
            allowed_source_refs=(policy_old_ref, employee_ref, request_ref),
            draft_claims=(
                _claim(
                    "obsolete-policy-rule",
                    ClaimType.RULE,
                    "The superseded policy requires only active employment.",
                    policy_old_ref,
                    DependencyRelation.GOVERNED_BY,
                ),
            ),
            critic_proposal=CriticProposal(),
        ),
    }
    return CompilerReferenceCatalog(
        registry=registry,
        scenarios=scenarios,
        sources_by_ref=sources_by_ref,
    )


def _artifact(
    artifact_id: str,
    *,
    logical_key: str,
    artifact_type: ArtifactType,
    source_type: SourceType,
    authority_rank: int,
) -> Artifact:
    return Artifact(
        artifact_id=artifact_id,
        artifact_type=artifact_type,
        logical_key=logical_key,
        owner_scope=REFERENCE_SCOPE,
        trust_class=TrustClass.AUTHORITATIVE,
        source_type=source_type,
        authority_rank=authority_rank,
        created_at=REFERENCE_NOW,
    )


def _ingest(
    artifact: Artifact,
    revision_label: str,
    value: dict[str, str],
) -> IngestedSource:
    return ingest_json_revision(
        artifact,
        revision_label=revision_label,
        value=value,
        created_at=REFERENCE_NOW,
        valid_from=REFERENCE_NOW,
        parser_version="reference-json-v1",
    )


def _add_ingested(
    registry: InMemorySourceRegistry,
    source: IngestedSource,
) -> None:
    registry.add_revision(source.revision)
    registry.add_representation(
        source.representation,
        source.fragments,
        fragment_values=source.fragment_values,
    )


def _claim(
    claim_local_id: str,
    claim_type: ClaimType,
    statement: str,
    source_ref: str,
    relation: DependencyRelation,
) -> ClaimDraft:
    return ClaimDraft(
        claim_local_id=claim_local_id,
        claim_type=claim_type,
        statement=statement,
        dependencies=[
            DependencyRef(
                source_ref=source_ref,
                relation=relation,
                materiality=Materiality.CRITICAL,
                purpose="Critical authorization input",
            )
        ],
        derived_from_claims=[],
        materiality=Materiality.CRITICAL,
        confidence=1.0,
    )


__all__ = [
    "REFERENCE_SCOPE",
    "REFERENCE_WORLD_SNAPSHOT",
    "CompilerReferenceCatalog",
    "FailClosedCompletenessCritic",
    "ReferenceAwareCompletenessCritic",
    "ReferenceScenarioSummary",
    "ReferenceSourceView",
    "build_reference_catalog",
    "ensure_reference_runtime",
    "reference_mission_id",
    "reference_request_id",
    "reference_scenario_id",
]
