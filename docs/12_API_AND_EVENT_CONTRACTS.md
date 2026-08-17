# 12 — API and Event Contracts

This document defines contracts, not implementation code.

## Control Plane REST API

### POST /api/missions/demo

Creates fresh seeded mission.

Response fields:

- mission_id
- status
- created_at

### POST /api/missions/{id}/start

Transitions eligible mission from CREATED to RUNNING and enqueues intake work.

### GET /api/missions/{id}

Returns mission summary/read model.

### GET /api/missions/{id}/timeline

Returns ordered domain events.

### GET /api/missions/{id}/graph

Returns nodes and dependency edges for visualization.

### GET /api/missions/{id}/commitments

Returns open/history commitments.

### POST /api/demo/policy/upgrade

Simulator-only. Creates v13 and emits `policy.version.changed`. Must not directly alter decisions.

### POST /api/demo/documents/pen-test

Simulator-only. Adds document artifact and emits `vendor.document.uploaded`.

### POST /api/agent-results

Agents submit structured work results. Control plane validates references and state preconditions before applying them.

## Event envelope

Every Pub/Sub/domain event should contain:

- event_id
- event_type
- mission_id (optional for global events)
- occurred_at
- producer
- correlation_id
- trace_id if available
- payload

## Important events

### policy.version.changed

Payload:

- policy_key
- old_version
- new_version
- artifact_id

### vendor.document.uploaded

Payload:

- vendor_id
- document_id
- document_type
- artifact_version/hash

### work.requested

Payload:

- work_item_id
- target_agent
- work_type
- input_refs

### work.completed

Payload:

- work_item_id
- outcome
- proposal_refs

### decision.stale

Domain event created by runtime, not by simulator.

Payload:

- decision_id
- cause_artifact_id
- propagation_root

## Idempotency

All mutating endpoints accept a request/event id. Duplicate requests must not create duplicate domain transitions.
