export type NodeKind = 'artifact' | 'evidence' | 'claim' | 'decision' | 'action'

export type NodeStatus =
  | 'CURRENT'
  | 'SUPERSEDED'
  | 'VALID'
  | 'STALE'
  | 'REVALIDATING'
  | 'READY'
  | 'BLOCKED'

export type RelationType =
  | 'SUPPORTED_BY'
  | 'GOVERNED_BY'
  | 'DERIVED_FROM'
  | 'REQUIRES'
  | 'AUTHORIZES'
  | 'CONTRADICTED_BY'

export interface GraphNodeDto {
  [key: string]: unknown
  id: string
  kind: NodeKind
  label: string
  status: NodeStatus
  artifact_id?: string
  artifact_type?: string
  logical_key?: string
  version?: string
  supersedes_artifact_id?: string | null
  evidence_id?: string
  evidence_kind?: string
  revision?: string
  decision_id?: string
  decision_type?: string
  outcome?: string
  execution_count?: number
  action_id?: string
  action_type?: string
}

export interface GraphEdgeDto {
  edge_id: string
  from_node_id: string
  to_node_id: string
  relation_type: RelationType
  critical: boolean
}

export interface RevalidationPlanDto {
  stale_decision_ids: string[]
  runnable_decision_ids: string[]
  waiting_decision_ids: string[]
  blocked_action_ids: string[]
  retained_decision_ids: string[]
  cause_by_node_id: Record<string, string>
}

export interface DomainEventDto {
  event_id: string
  event_type: string
  payload: Record<string, string>
}

export interface DispatchRecordDto {
  dispatch_id: string
  request_id: string
  decision_id: string
  work_type: string
  status: string
}

export interface GraphReadModel {
  mission_id: string
  phase: 'INITIAL' | 'DRIFTED' | 'REVALIDATING'
  summary: {
    stale: number
    preserved: number
    blocked: number
  }
  nodes: GraphNodeDto[]
  edges: GraphEdgeDto[]
  plan: RevalidationPlanDto
  causes: Record<string, string>
  events: DomainEventDto[]
  dispatches: DispatchRecordDto[]
}

export type ScenarioPhase =
  | 'CREATED'
  | 'BASELINE_WAITING'
  | 'POLICY_DRIFT'
  | 'MISSING_EVIDENCE'
  | 'COMPLETED'

export type NextAction =
  | 'START'
  | 'INJECT_POLICY'
  | 'RUN_REVALIDATION'
  | 'UPLOAD_PEN_TEST'
  | 'RESET'

export interface RouteCheckpoint {
  id: string
  label: string
  status: string
  kind: 'work' | 'artifact' | 'evidence' | 'decision' | 'commitment' | 'action'
  preserved?: boolean
}

export interface AgentLane {
  agent_id: string
  label: string
  status: string
  checkpoints: RouteCheckpoint[]
}

export interface CommitmentDto {
  commitment_id: string
  event_type: string
  predicate: Record<string, string>
  status: string
  created_at: string
}

export interface TimelineEventDto {
  audit_event_id: string
  event_sequence: number
  event_type: string
  payload: Record<string, unknown>
  occurred_at: string
}

export interface MissionControlReadModel {
  mission: {
    mission_id: string
    status: string
    created_at: string
    updated_at: string
  }
  subject: { id: string; name: string }
  scenario_phase: ScenarioPhase
  next_action: NextAction
  execution_mode: 'LOCAL_DETERMINISTIC' | 'GOOGLE_ADK_GEMINI'
  current_policy: string
  vendor_status: 'PENDING' | 'ACTIVE'
  agent_lanes: AgentLane[]
  commitments: CommitmentDto[]
  side_effects: Array<{ side_effect_id: string; effect_type: string; status: string }>
  timeline: TimelineEventDto[]
  graph: GraphReadModel
}

export interface MissionSummary {
  mission_id: string
  mission_type: string
  subject_id: string
  status: string
  revision: number
  event_sequence: number
  created_at: string
  updated_at: string
  counts: {
    work_items: number
    open_commitments: number
    side_effects: number
  }
}

export interface BudgetEvidenceDto {
  limit_usd: string
  spent_usd: string
  reserved_usd: string
  remaining_usd: string
  settled_calls: number
  reserved_calls: number
  pricing_version: string
}

export interface ProviderEvidenceDto {
  status: 'PASS' | 'FAIL' | 'BLOCKED'
  provider: string
  model: string
  reason?: string | null
  credentials_configured: boolean
  report_run_id?: string | null
  budget?: BudgetEvidenceDto | null
}

export interface CompilerEvidenceDto {
  deterministic_reference: ProviderEvidenceDto
  openai: ProviderEvidenceDto
  gemini: ProviderEvidenceDto
}

export interface ReferenceScenarioDto {
  scenario_id: string
  label: string
  summary: string
  expected_disposition: string
}

export interface CompilerLabStatusDto {
  execution_mode: 'DETERMINISTIC_REFERENCE'
  scenarios: ReferenceScenarioDto[]
  evidence: CompilerEvidenceDto
}

export interface ReferenceSourceDto {
  source_ref: string
  logical_key: string
  artifact_type: string
  source_type: string
  trust_class: string
  authority_rank: number
  revision_label: string
  source_hash: string
  fragment_hash: string
  logical_path: string
  content: unknown
  historical: boolean
}

export interface CompilerDependencyDto {
  source_ref: string
  relation: string
  materiality: string
  purpose?: string | null
}

export interface CompilerClaimDraftDto {
  claim_local_id: string
  claim_type: string
  statement: string
  dependencies: CompilerDependencyDto[]
  derived_from_claims: string[]
  materiality: string
  confidence: number
}

export interface CompilerFindingDto {
  finding_id: string
  code?: string
  stage?: string
  finding_type?: string
  severity: string
  message: string
  source_ref?: string | null
  candidate_ref?: string | null
  claim_local_id?: string | null
  blocking?: boolean
}

export interface CompilerContradictionDto {
  finding_id: string
  claim_or_topic: string
  source_ref_a: string
  source_ref_b: string
  severity: string
  precedence_rule_applied?: string | null
  resolution: string
}

export interface CompilerAggregateDto {
  request: {
    request_id: string
    mission_id: string
    work_item_id: string
    agent_id: string
    world_snapshot_id: string
    expected_mission_revision: number
    decision_type: string
    risk_class: string
    owner_scope: string
    allowed_source_refs: string[]
    allow_historical: boolean
    created_at: string
  }
  state: 'REQUESTED' | 'DRAFT_RECEIVED' | 'COMPILED'
  draft?: {
    request_id: string
    decision_type: string
    proposed_outcome: string
    claims: CompilerClaimDraftDto[]
    decision_dependencies: CompilerDependencyDto[]
    unresolved_questions: Array<{ question: string; required_source_type: string; blocking: boolean }>
    rationale_summary: string
    model_metadata: Record<string, unknown>
  } | null
  result?: {
    compilation_id: string
    request_id: string
    status: string
    decision_candidate?: { decision_id: string; decision_type: string; outcome: string; rationale_summary: string } | null
    canonical_claims: Array<{ claim_id: string; claim_local_id: string; claim_type: string; statement: string; materiality: string; confidence: number }>
    canonical_edges: Array<{ edge_id: string; source_kind: string; source_id: string; target_kind: string; target_id: string; relation: string; materiality: string; purpose?: string | null }>
    validation_findings: CompilerFindingDto[]
    critic_findings: CompilerFindingDto[]
    contradictions: CompilerContradictionDto[]
    compiler_version: string
    validation_policy_version: string
    compilation_hash?: string | null
    model_metadata?: Record<string, unknown> | null
    critic_model_metadata?: Record<string, unknown> | null
    executed_stages: Array<'VALIDATED' | 'REVIEWED' | 'COMPILED'>
  } | null
  outbox: Array<Record<string, unknown>>
  updated_at: string
}

export interface RuntimeReceiptDto {
  duplicate: boolean
  mission_id: string
  mission_revision: number
  decision_id: string
  claim_ids: string[]
  evidence_ids: string[]
  compilation_id: string
  compilation_hash: string
  audit_event_id: string
  audit_link: string
}

export interface CompilerStageTraceDto {
  stage: 'REQUESTED' | 'DRAFT_RECEIVED' | 'VALIDATED' | 'REVIEWED' | 'COMPILED' | 'RUNTIME_ACCEPTED'
  owner: 'COMPILER' | 'MODEL PROPOSAL' | 'RUNTIME'
  state: 'DONE' | 'ACTIVE' | 'SKIPPED' | 'WAITING'
}

export interface CompilerLabViewDto {
  scenario_id: string
  scenario_label: string
  scenario_summary: string
  execution_mode: 'DETERMINISTIC_REFERENCE'
  aggregate: CompilerAggregateDto
  sources: ReferenceSourceDto[]
  evidence: CompilerEvidenceDto
  stage_trace: CompilerStageTraceDto[]
  runtime_receipt?: RuntimeReceiptDto | null
}

export interface ContinuumApi {
  listMissions(limit?: number): Promise<MissionSummary[]>
  createDemo(requestId: string): Promise<{ mission_id: string }>
  start(missionId: string, requestId: string): Promise<unknown>
  getControl(missionId: string): Promise<MissionControlReadModel>
  upgradePolicy(missionId: string, eventId: string): Promise<GraphReadModel>
  revalidate(missionId: string, requestId: string): Promise<GraphReadModel>
  uploadPenTest(missionId: string, eventId: string): Promise<unknown>
  getCompilerLabStatus?(): Promise<CompilerLabStatusDto>
  runCompilerScenario?(scenarioId: string, requestId: string): Promise<CompilerLabViewDto>
  acceptCompilerScenario?(requestId: string): Promise<CompilerLabViewDto>
}
