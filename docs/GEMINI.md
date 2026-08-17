# GEMINI.md — Build Contract for Continuum

You are implementing Continuum for a Google Agent hackathon. Treat the documents in this repository as the product and technical contract.

## Mandatory behavior

1. Read `README.md` and all numbered design documents before implementing the core runtime.
2. Execute `18_BUILD_PLAN.md` in order.
3. At the end of every phase:
   - run the listed verification;
   - record what passed/failed;
   - do not proceed when a required acceptance criterion fails.
4. Never replace deterministic runtime semantics with an LLM judgment merely because it is easier.
5. Gemini may propose dependencies and explanations; the runtime must persist structured dependency edges and apply deterministic invalidation rules to them.
6. External side effects must be idempotent or explicitly marked unsafe.
7. Every stale/invalid decision must be explainable from stored evidence and dependency edges.
8. The demo must use real persisted state, real event transitions, and real Gemini/ADK agent executions. UI-only scripted animation does not count.

## Preferred stack

- Agent framework: Google ADK, Python 3.11+
- Model: Gemini 3.5 Flash or newer through Vertex AI / Gemini API as allowed by the contest
- Agent deployment: Gemini Enterprise Agent Runtime where practical
- Web/API control plane: FastAPI on Cloud Run
- UI: React/Next.js + TypeScript
- Durable domain state: Firestore
- Async wakeups/events: Pub/Sub
- Long-term semantic/user memory: Agent Platform Memory Bank, but **not** as the source of truth for decisions, commitments, or side effects
- Observability: OpenTelemetry + Google Cloud Observability

## Do not overbuild

Do not create a generic workflow builder, generic IAM system, generic registry marketplace, generic vector database, or Temporal replacement.

## Core thesis check

At any point, ask:

> If Security Policy v12 changes to v13 while the mission is waiting, can the system deterministically show which old decisions are stale, which remain valid, and which branch must rerun?

If the answer is no, stop adding features and repair the core.
