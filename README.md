# Continuum

Continuum is a mission-control runtime for long-lived enterprise agents. It prevents agents from continuing blindly when the assumptions behind earlier decisions are no longer valid, then selectively revalidates only the affected execution branches.

This repository is the canonical product and architecture handoff for a Google All Things Agentic hackathon prototype in the Fortified Enterprise Fleet track.

## Current status

Four product milestones are complete:

1. **Phase G falsification gate:** Policy v12 → v13 deterministically makes D42 and D50 stale, preserves D43, blocks ActivateVendor, and dispatches only D42.
2. **Local semantic runtime:** durable Mission/WorkItem state machines, Commitment matching, immutable Decision supersession, Side Effect Ledger safety, audit/outbox, optimistic concurrency, idempotent inbox, SQLite restart recovery, and a unified runtime/graph API.
3. **Local Mission Control product:** a browser-operated Acme Analytics scenario with three semantic agent lanes, policy-drift impact, preserved work, durable missing-evidence wait, immutable D57/D58 supersession, and exactly-once vendor activation.
4. **Google integration foundation:** bounded Google ADK/Gemini agents, a transactional Firestore repository, durable Pub/Sub outbox relay, Cloud Trace instrumentation, and a production Cloud Run container/deployment path.

The Vendor, Security, and Procurement agents are implemented with Google ADK and typed Gemini output contracts. Firestore, Pub/Sub, Cloud Trace, and Cloud Run adapters are implemented and locally contract-tested. A live deployment and hosted execution evidence still require a Google Cloud project and Application Default Credentials; the repository does not claim those unverified results. The UI and `/api/health` disclose the active execution, persistence, event, and telemetry modes.

## Google ADK + Gemini mode

The default remains deterministic and credential-free. To run the same browser story through all three real ADK agents, configure either an AI Studio key or Vertex AI credentials:

```bash
cp .env.example .env
export CONTINUUM_AGENT_MODE=google_adk
export CONTINUUM_GEMINI_MODEL=gemini-3.6-flash
export GEMINI_API_KEY='...'
make dev
```

For Vertex AI, set `GOOGLE_GENAI_USE_VERTEXAI=TRUE`, `GOOGLE_CLOUD_PROJECT`, and `GOOGLE_CLOUD_LOCATION` instead. Google mode fails fast when neither credential path is configured.

Gemini materially performs six bounded reviews in the canonical story: Vendor, Security, and Procurement at baseline; Security after v13; then Security and Procurement after the pen test arrives. Agents can only return typed proposals and stable dependency references. The runtime validates references, owns invalidation and Decision transitions, and commits activation through the Side Effect Ledger.

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

The production image serves the built React application and FastAPI API from one Cloud Run container:

```bash
docker build -t continuum:local .
docker run --rm -p 8080:8080 continuum:local
curl http://127.0.0.1:8080/api/health
```

For a Google Cloud deployment, use `scripts/deploy-google-cloud.sh PROJECT_ID REGION`. It provisions the required APIs, a Native-mode Firestore database, Pub/Sub topic, least-purpose runtime service account roles, and deploys the source container with Vertex AI, Firestore, Pub/Sub, and Cloud Trace enabled. See [Google Cloud deployment](docs/24_GOOGLE_CLOUD_DEPLOYMENT.md).

After deployment, `CONTINUUM_EXPECT_CLOUD=1 scripts/verify-deployment.sh CLOUD_RUN_URL 3` executes the canonical mission three times and fails unless every semantic and cloud-mode assertion passes.

## Durable runtime API

```text
POST /api/missions/demo
POST /api/missions/{mission_id}/start
GET  /api/missions/{mission_id}
GET  /api/missions/{mission_id}/timeline
GET  /api/missions/{mission_id}/commitments
GET  /api/missions/{mission_id}/control
POST /api/events
POST /api/demo/policy/upgrade
POST /api/missions/{mission_id}/revalidate
POST /api/demo/documents/pen-test
```

The recommended flow is the browser UI. Its single contextual action walks through:

```text
Start mission
→ Inject Policy v13
→ Run affected branch
→ Upload pen test · +7 days
→ Vendor ACTIVE / Mission COMPLETED
```

The same flow can be driven through the API:

```bash
curl -s http://127.0.0.1:8000/api/missions/demo \
  -H 'content-type: application/json' \
  -d '{"request_id":"create-1"}'

curl -s http://127.0.0.1:8000/api/missions/MISSION_ID/start \
  -H 'content-type: application/json' \
  -d '{"request_id":"start-1"}'

curl -s http://127.0.0.1:8000/api/demo/policy/upgrade \
  -H 'content-type: application/json' \
  -d '{"mission_id":"MISSION_ID","event_id":"policy-1"}'

curl -s http://127.0.0.1:8000/api/missions/MISSION_ID/revalidate \
  -H 'content-type: application/json' \
  -d '{"request_id":"revalidate-1"}'

curl -s http://127.0.0.1:8000/api/demo/documents/pen-test \
  -H 'content-type: application/json' \
  -d '{"mission_id":"MISSION_ID","event_id":"pen-test-1"}'
```

The start command first establishes valid Policy v12 decisions, then leaves the Mission waiting on a Procurement activation-window Commitment. Only after Policy v13 invalidates the affected branch does Security revalidation create a pen-test Commitment. The matching document event atomically satisfies it, creates D57/D58 as immutable successors, commits activation once, and completes the Mission. Replaying any request or event ID returns the original result without another transition.

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
7. Review the [Mission Control product design](docs/superpowers/specs/2026-08-18-mission-control-product-design.md) and [local product report](docs/reports/mission-control-local-product-report.md).

## Explicit non-goals

Continuum is not a generic agent builder, workflow editor, IAM platform, generic memory platform, or Temporal replacement.
