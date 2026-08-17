# 04 — Domain Model

## Entity: Mission

Fields:

- `mission_id`
- `template_id`
- `title`
- `status`
- `created_at`
- `updated_at`
- `current_epoch`
- `active_policy_versions`
- `owner`
- `demo_clock`

## Entity: WorkItem

Represents a unit of agent work.

Fields:

- `work_item_id`
- `mission_id`
- `agent_type`
- `work_type`
- `status`
- `input_refs`
- `output_refs`
- `attempt`
- `created_at`
- `completed_at`

States:

`PENDING -> DISPATCHED -> RUNNING -> SUCCEEDED | FAILED | WAITING | CANCELLED`

## Entity: Evidence

Facts observed by tools or humans. Evidence must not contain an authoritative verdict.

Fields:

- `evidence_id`
- `mission_id`
- `kind`
- `source_type`
- `source_ref`
- `content_hash`
- `revision`
- `observed_at`
- `payload_summary`

## Entity: Decision

Fields:

- `decision_id`
- `mission_id`
- `decision_type`
- `outcome`
- `agent_id`
- `reasoning_summary`
- `status`: `VALID | STALE | REVALIDATING | INVALID | SUPERSEDED`
- `created_at`
- `supersedes_decision_id`

## Entity: DependencyEdge

Directed edge from source to dependent node.

Fields:

- `edge_id`
- `mission_id`
- `from_node_type`
- `from_node_id`
- `to_node_type`
- `to_node_id`
- `relation_type`
- `criticality`
- `created_at`

Typical relation types:

- `SUPPORTED_BY`
- `GOVERNED_BY`
- `DERIVED_FROM`
- `REQUIRES`
- `AUTHORIZES`
- `BLOCKS`

## Entity: Commitment

Fields:

- `commitment_id`
- `mission_id`
- `owner_agent`
- `trigger_type`
- `match_predicate`
- `resume_work_type`
- `status`: `OPEN | SATISFIED | EXPIRED | CANCELLED`
- `created_at`
- `satisfied_by_event_id`

## Entity: SideEffect

Fields:

- `side_effect_id`
- `mission_id`
- `action_type`
- `idempotency_key`
- `status`: `INTENDED | EXECUTING | COMMITTED | FAILED | UNKNOWN`
- `external_reference`
- `request_hash`
- `response_hash`
- `created_at`
- `committed_at`

## Entity: WorldArtifact

Versioned external state.

Examples:

- Security Policy v12/v13
- Vendor Profile revision 7/8
- SOC2 document hash
- agent permission snapshot

Fields:

- `artifact_id`
- `artifact_type`
- `logical_key`
- `version`
- `content_hash`
- `effective_at`
- `supersedes`

## Hard invariants

1. Evidence cannot directly change a decision's status.
2. Every material decision must have at least one dependency.
3. A stale decision cannot authorize a new irreversible side effect.
4. A committed side effect with the same idempotency key cannot execute twice.
5. Revalidation creates a new decision or explicitly restores validity with a recorded revalidation event; it never silently edits history.
6. Every commitment can be satisfied at most once.
7. Every state transition is appended to the audit ledger.
