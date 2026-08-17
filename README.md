# Continuum

Continuum is a mission-control runtime concept for long-lived enterprise agents. It detects when the assumptions behind earlier AI decisions have become stale and selectively revalidates only the affected execution branches.

This repository is the canonical product and architecture handoff for a Google All Things Agentic hackathon prototype in the Fortified Enterprise Fleet track. It currently contains only the Phase G falsification prototype; the full product build has not started.

## Current gate

The next build is limited to the 36-hour falsification prototype:

```text
Policy v12 -> v13
D42 -> STALE
D43 -> VALID
downstream(D42) -> STALE
ActivateVendor -> BLOCKED
selective branch re-execution
```

This gate passed on 2026-08-18. The product owner explicitly waived the proposed five-person observation and accepted the deterministic tests, real-browser E2E, and captured UI evidence as sufficient for this hackathon gate. This decision does not itself start the full-product build.

## Run the gate

Prerequisites: Python 3.11+, [uv](https://docs.astral.sh/uv/), Node.js 20+, npm, and Chromium for Playwright.

```bash
make setup
npx --prefix frontend playwright install chromium
make test
make test-e2e
```

Start the interactive prototype at `http://127.0.0.1:5173`:

```bash
make dev
```

The screen starts from a fresh canonical mission. Select `Inject policy v13` and confirm the deterministic outcome:

```text
D42              STALE
D43              VALID / PRESERVED
D50              STALE / WAITING
ActivateVendor   BLOCKED
Run now          D42 only
```

Selecting `Run affected branch` changes only D42 to `REVALIDATING`; it does not invent a replacement approval.

## Gate API

The local FastAPI control plane exposes exactly the four gate operations:

```text
POST /api/demo/reset
POST /api/demo/policy/upgrade
GET  /api/missions/{mission_id}/graph
POST /api/missions/{mission_id}/revalidate
```

The simulator creates world input only. Decision and Action state transitions remain owned by the deterministic domain services.

## Explicit exclusions

This gate intentionally contains no Gemini or Google ADK integration, Firestore/Pub/Sub adapter, cloud deployment, commitment protocol, real side effects, generic agent builder, workflow editor, IAM system, memory platform, or Temporal replacement. Those hypotheses remain untested here.

## Start here

1. Read [AGENTS.md](AGENTS.md).
2. Read the [design-pack index](docs/README.md).
3. Review the [36-hour falsification gate](docs/17_36H_FALSIFICATION_GATE.md).
4. Review the approved [Phase G design specification](docs/superpowers/specs/2026-08-17-falsification-gate-design.md).
5. Follow the [implementation plan](docs/superpowers/plans/2026-08-17-falsification-gate.md).
6. Read the [gate report](docs/reports/36h-gate-report.md) for observed evidence and the recorded owner waiver.

## Core invariant

Gemini may propose decisions and dependencies. The Continuum runtime owns deterministic invalidation and canonical state transitions.

Semantic Resume is not ordinary checkpoint/resume.
