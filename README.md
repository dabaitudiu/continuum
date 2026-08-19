# Continuum

[![CI](https://github.com/dabaitudiu/continuum/actions/workflows/ci.yml/badge.svg)](https://github.com/dabaitudiu/continuum/actions/workflows/ci.yml)

Continuum is a mission-control runtime for long-lived enterprise agents. It prevents agents from continuing blindly when the assumptions behind earlier decisions are no longer valid, then selectively revalidates only the affected execution branches.

This repository is the canonical product and architecture handoff for a Google All Things Agentic hackathon prototype in the Fortified Enterprise Fleet track.

## Current product boundary

The current product has two credential-free surfaces: Mission Control proves Semantic Resume end to end, and Compiler Lab exposes the Semantic Dependency Compiler's exact source, claim, validation, and runtime-acceptance boundary. Live-model evidence remains a separate acceptance lane and is never inferred from deterministic reference fixtures.

Four current-scope product milestones are implemented:

1. **Phase G falsification gate:** Policy v12 → v13 deterministically makes D42 and D50 stale, preserves D43, blocks ActivateVendor, and dispatches only D42.
2. **Local semantic runtime:** durable Mission/WorkItem state machines, Commitment matching, immutable Decision supersession, Side Effect Ledger safety, audit/outbox, optimistic concurrency, idempotent inbox, SQLite restart recovery, and a unified runtime/graph API.
3. **Local Mission Control product:** a browser-operated Acme Analytics scenario with three semantic agent lanes, policy-drift impact, preserved work, durable missing-evidence wait, immutable D57/D58 supersession, and exactly-once vendor activation.
4. **Semantic Dependency Compiler v1 Phases B–G:** typed Decision/Claim/Dependency IR, deterministic validation and canonicalization, provider-neutral reasoner/critic adapters, a 120-case three-domain benchmark, durable compiler repositories, runtime acceptance, and the browser-operated Compiler Lab. Its model method failed acceptance and is now a legacy implementation under redesign, not the final compiler architecture.

Module 01 is not declared fully accepted: its deterministic reference lane passes, but the authenticated OpenAI lane completed and **failed** the model-quality gate (98.21% critical recall, 65.48% precision, 0% contradiction recall, 42.50% outcome compliance, and 80.56% stale escape). Live Gemini remains `BLOCKED` because no Gemini/Vertex credentials were available, and the module definition of done still explicitly requires live Gemini evidence. See [the compiler benchmark report](docs/reports/module-01-dependency-compiler.md) and [the current P0 matrix](docs/continuum_module_01_semantic_dependency_compiler/13_ACCEPTANCE_MATRIX_AND_KILL_CRITERIA.md).

The preserved-report audit found that the 98.21% figure is proposal-union recall rather than accepted canonical coverage, and that 58/72 historical “stale escapes” were compilations that never entered Runtime. A bounded live paired ablation then triggered K3 for the current critic: it recovered 0 omissions, detected 0 contradictions, added 4 false-positive refs, introduced 5 spurious blocks, and reduced acceptance from 8/30 to 3/30. See [the failure analysis](docs/reports/module-01-failure-analysis-v1.md) and [the paired critic ablation](docs/reports/module-01-critic-ablation.md).

On 2026-08-19 the product owner selected Option B's direction、rejected the vague critic, and rejected the first concrete specification on 11 P0 architectural blockers. [Replacement Architecture Revision 2](docs/continuum_module_01_semantic_dependency_compiler/15_REPLACEMENT_ARCHITECTURE.md) adds independent governing-obligation coverage、deterministic proof-selected materiality/contradiction impact、three-state entailment、complete source/policy provenance、stable semantic proof identity、paired injection evaluation、an externally held blind holdout and unsupported-logic fail-closed behavior. It awaits product-owner review and is not implemented. Do not write the v2 plan、modify production compiler、generate/read blind holdout cases、call live models、run full paid DEV or start Module 02.

An optional Google integration foundation also exists: bounded Google ADK/Gemini agents, a transactional Firestore repository, durable Pub/Sub outbox relay, Cloud Trace instrumentation, and a Cloud Run deployment path. These adapters are locally contract-tested but have no live-cloud evidence, and they are not counted as a completed product milestone. The UI and `/api/health` always disclose the active execution, persistence, event, and telemetry modes.

## Optional Google ADK + Gemini mode

The default remains deterministic and credential-free. To run the same browser story through all three real ADK agents, configure either an AI Studio key or Vertex AI credentials:

```bash
cp .env.example .env
export CONTINUUM_AGENT_MODE=google_adk
export CONTINUUM_GEMINI_MODEL=gemini-3.6-flash
export GEMINI_API_KEY='...'
make dev
```

For Vertex AI, set `GOOGLE_GENAI_USE_VERTEXAI=TRUE`, `GOOGLE_CLOUD_PROJECT`, and `GOOGLE_CLOUD_LOCATION` (recommended: `global`) instead. Google mode fails fast when neither credential path is configured.

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
Mission Control stores the active Mission pointer in the browser URL and local storage. Reloading `/missions/{mission_id}` restores the same durable Mission, including an open Commitment; only an explicit Reset creates a new namespace.
The Mission history view lists recent durable namespaces from the runtime store and can reopen any prior Mission without replaying completed work.

Open **Compiler Lab** in the top navigation to execute four bounded reference cases: accepted dependencies, a missing governing clause, conflicting equal-rank authorities, and a stale Policy v12 reference. The reference adapter is intentionally labeled deterministic and does not count as model evidence. Only an accepted immutable compilation exposes the demo Runtime commit action; rejected or review-required results cannot mutate Runtime.

If an OpenAI key is supplied, the evidence benchmark can be run through the real Responses API. The SQLite ledger reserves worst-case cost before every request and enforces a cumulative hard cap of **$10** across runs. The audited OpenAI client disables SDK retries, pins the default service tier, prices cache writes separately at the documented premium, and retains conservative UNKNOWN holds for ambiguous or pre-v2 exposure:

```bash
cd backend
OPENAI_API_KEY='...' uv run python -m app.compiler.benchmark.cli run \
  --suite evidence \
  --budget-ledger data/openai-benchmark-budget.db \
  --output-dir ../docs/reports
```

The command exits non-zero after writing the report whenever any selected lane is `FAIL` or `BLOCKED`. The committed result contains an OpenAI metric-gate `FAIL` and a credential-blocked Gemini lane, so inspect the individual statuses rather than inferring one cause from the process exit code. An unaudited `CONTINUUM_OPENAI_MODEL` override is rejected instead of weakening the budget guard.

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

## Semantic Dependency Compiler API

```text
POST /api/compiler/requests
POST /api/compiler/{request_id}/draft
POST /api/compiler/{request_id}/compile
GET  /api/compiler/{request_id}
POST /api/compiler/{request_id}/accept        # runtime capability only

GET  /api/demo/compiler/status
POST /api/demo/compiler/scenarios/{scenario_id}
GET  /api/demo/compiler/{request_id}
POST /api/demo/compiler/{request_id}/accept   # registered reference fixtures only
```

Compiler requests, drafts, results, findings, outbox events, compilation hashes, and Runtime receipts are immutable/idempotent under their request identity. The generic `/api/compiler` surface is internal and disabled unless `CONTINUUM_COMPILER_API_CAPABILITY` is configured; callers then supply `X-Continuum-Compiler-Capability`. Acceptance additionally requires `X-Continuum-Runtime-Capability`. The public product demo exposes only fixed, server-authored scenarios and separately accepts only a reference request registered by the server-side runner.

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
8. Use the [submission architecture](docs/submission/ARCHITECTURE.md), [four-minute demo script](docs/submission/DEMO_SCRIPT.md), and [evidence checklist](docs/submission/EVIDENCE_CHECKLIST.md) for final delivery.
9. Review the [Compiler Lab product design](docs/superpowers/specs/2026-08-19-compiler-lab-product-design.md), [Compiler Lab product report](docs/reports/compiler-lab-product-report.md), and [Module 01 benchmark report](docs/reports/module-01-dependency-compiler.md).

## Explicit non-goals

Continuum is not a generic agent builder, workflow editor, IAM platform, generic memory platform, or Temporal replacement.
