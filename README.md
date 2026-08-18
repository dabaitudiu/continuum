# Continuum

Continuum is a mission-control runtime for long-lived enterprise agents. It prevents agents from continuing blindly when the assumptions behind earlier decisions are no longer valid, then selectively revalidates only the affected execution branches.

This repository is the canonical product and architecture handoff for a Google All Things Agentic hackathon prototype in the Fortified Enterprise Fleet track.

## Current status

Two product milestones are complete:

1. **Phase G falsification gate:** Policy v12 → v13 deterministically makes D42 and D50 stale, preserves D43, blocks ActivateVendor, and dispatches only D42.
2. **Local semantic runtime:** durable Mission/WorkItem state machines, Commitment matching, immutable Decision supersession, Side Effect Ledger safety, audit/outbox, optimistic concurrency, idempotent inbox, SQLite restart recovery, and a unified runtime/graph API.

The full browser Mission Control, three Google ADK/Gemini agents, Firestore/Pub/Sub adapters, Google Cloud deployment, and OpenTelemetry export remain subsequent milestones. Local adapters are not presented as completion of those cloud requirements.

## Run locally

Prerequisites: Python 3.11+, [uv](https://docs.astral.sh/uv/), Node.js 20+, npm, and Chromium for Playwright.

```bash
make setup
npx --prefix frontend playwright install chromium
make test
make test-e2e
make dev
```

The UI is available at `http://127.0.0.1:5173`; FastAPI runs at `http://127.0.0.1:8000`.

Runtime state is stored in `backend/data/continuum.db` by default. Set `CONTINUUM_DB_PATH` to use another explicit SQLite file. Demo reset creates a new Mission namespace and does not delete audit history.

## Durable runtime API

```text
POST /api/missions/demo
POST /api/missions/{mission_id}/start
GET  /api/missions/{mission_id}
GET  /api/missions/{mission_id}/timeline
GET  /api/missions/{mission_id}/commitments
POST /api/events
```

Minimal local flow:

```bash
curl -s http://127.0.0.1:8000/api/missions/demo \
  -H 'content-type: application/json' \
  -d '{"request_id":"create-1"}'

curl -s http://127.0.0.1:8000/api/missions/MISSION_ID/start \
  -H 'content-type: application/json' \
  -d '{"request_id":"start-1"}'

curl -s http://127.0.0.1:8000/api/events \
  -H 'content-type: application/json' \
  -d '{
    "event_id":"evt-pen-1",
    "event_type":"vendor.document.uploaded",
    "mission_id":"MISSION_ID",
    "producer":"enterprise-simulator",
    "correlation_id":"evt-pen-1",
    "payload":{
      "vendor_id":"ACME",
      "document_id":"document:pen-test-2026",
      "document_type":"PEN_TEST"
    }
  }'
```

The start command leaves the Mission in `WAITING` with an open pen-test Commitment. A mismatched document event is recorded but ignored. The matching event atomically satisfies the Commitment, resumes the waiting WorkItem, advances the Mission to `RUNNING`, and appends audit/outbox records. Replaying any request or event ID returns the original result without another transition.

## Decision Graph API

The original falsification-gate endpoints remain compatible and now persist through the same runtime aggregate:

```text
POST /api/demo/reset
POST /api/demo/policy/upgrade
GET  /api/missions/{mission_id}/graph
POST /api/missions/{mission_id}/revalidate
```

The simulator creates world input only. Decision and Action transitions remain owned by deterministic domain services. Graph state, processed IDs, audit records, and Mission state survive a new SQLite repository instance.

## Safety invariants

- Gemini or an agent may propose decisions and dependencies; the runtime owns canonical state.
- `WAITING` WorkItems require an open Commitment.
- Only an exact event type and predicate can satisfy a Commitment.
- Old Decisions are retained and superseded; they are never rewritten as new conclusions.
- Only `VALID` Decisions can authorize side effects.
- Unknown side-effect outcomes require reconciliation before retry.
- State, inbox, audit, and outbox commit atomically under an expected Mission revision.
- Semantic Resume is not ordinary checkpoint/resume.

## Start here

1. Read [AGENTS.md](AGENTS.md).
2. Read the [design-pack index](docs/README.md).
3. Review the [36-hour gate report](docs/reports/36h-gate-report.md).
4. Review the [local semantic runtime design](docs/superpowers/specs/2026-08-18-local-semantic-runtime-design.md).
5. Follow the [local semantic runtime implementation plan](docs/superpowers/plans/2026-08-18-local-semantic-runtime.md).
6. Read the [local runtime evidence report](docs/reports/local-semantic-runtime-report.md).

## Explicit non-goals

Continuum is not a generic agent builder, workflow editor, IAM platform, generic memory platform, or Temporal replacement.
