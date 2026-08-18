export type NodeKind = 'artifact' | 'evidence' | 'decision' | 'action'

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
  execution_mode: 'LOCAL_DETERMINISTIC'
  current_policy: string
  vendor_status: 'PENDING' | 'ACTIVE'
  agent_lanes: AgentLane[]
  commitments: CommitmentDto[]
  side_effects: Array<{ side_effect_id: string; effect_type: string; status: string }>
  timeline: TimelineEventDto[]
  graph: GraphReadModel
}

export interface ContinuumApi {
  createDemo(requestId: string): Promise<{ mission_id: string }>
  start(missionId: string, requestId: string): Promise<unknown>
  getControl(missionId: string): Promise<MissionControlReadModel>
  upgradePolicy(missionId: string, eventId: string): Promise<GraphReadModel>
  revalidate(missionId: string, requestId: string): Promise<GraphReadModel>
  uploadPenTest(missionId: string, eventId: string): Promise<unknown>
}
