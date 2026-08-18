# Continuum — submission draft

## Tagline

Semantic resume for long-lived enterprise agents.

## Problem

Long-running agents pause on approvals, documents, and real-world events. While they wait, policies, permissions, vendor data, and other assumptions can change. Ordinary checkpoint/resume restores execution position, but it does not prove that earlier AI decisions are still valid. Restarting everything is safer but wasteful; blindly continuing is unsafe.

## What Continuum does

Continuum records why each consequential Decision was valid: the exact policy, evidence, artifact version, and upstream Decision dependencies. When the world changes, a deterministic runtime propagates invalidation through that graph, preserves unaffected work, blocks stale authorization, and dispatches only the affected branch for revalidation.

The demo onboards Acme Analytics. Policy v12 initially authorizes the route. When v13 adds a penetration-test requirement, Security decision D42 becomes stale, downstream Procurement decision D50 becomes stale, independent financial decision D43 remains valid, and activation is blocked. A durable Commitment waits for the missing document. When the document event arrives, fresh Decisions D57 and D58 supersede the stale Decisions and activation commits exactly once.

## How it is built

- React Mission Control for route, Decision Graph, causal explanation, Commitment, event history, and Mission recovery views.
- FastAPI control plane with deterministic Mission and WorkItem state machines.
- Provenance graph invalidation and selective revalidation planning.
- Durable Commitments with exact event-type and predicate matching.
- Side Effect Ledger with idempotency and reconciliation states.
- Google ADK Vendor, Security, and Procurement agents with typed Gemini proposals.
- Firestore transactional Mission aggregates and query projections.
- Pub/Sub transactional-outbox delivery.
- OpenTelemetry export to Google Cloud Trace.
- One Cloud Run container serving both UI and API.

## Material use of Gemini and ADK

Gemini performs bounded vendor, security, and procurement reviews at baseline and after policy drift. It interprets current policy and evidence, proposes dependency references, explains missing evidence, and produces typed outcomes. The control plane rejects unknown references and owns every canonical transition. Replacing Gemini with deterministic fixtures preserves testability, but the cloud demo must show real Gemini-generated `agent.result.accepted` events and `GOOGLE_ADK_GEMINI` execution mode.

## What was falsified

- Embeddings or similarity search are insufficient for authorization-sensitive provenance.
- Generic checkpoint/resume does not detect invalidated assumptions.
- Letting the model own invalidation makes safety nondeterministic.
- Restart-all hides the value of preserving independent completed work.

## Technical proof

- Public repository: <https://github.com/dabaitudiu/continuum>
- CI product gate: <https://github.com/dabaitudiu/continuum/actions/runs/32123929626>
- Hosted product: `PENDING_CLOUD_RUN_URL`
- Architecture: [`ARCHITECTURE.md`](ARCHITECTURE.md)
- Demo video: `PENDING_PUBLIC_VIDEO_URL`

## Accomplishments

- A generic invalidation kernel with no scenario-specific node IDs.
- Durable Mission recovery across browser reloads and repository restarts.
- Exact Commitment matching and duplicate-event idempotency.
- Immutable Decision supersession and exactly-once activation.
- One browser-operated story with no terminal interaction.
- Contract-equivalent memory, SQLite, and Firestore repositories.

## What we learned

The hardest part of long-running agents is not remembering conversation text or a program counter. It is preserving the causal basis for decisions, then proving which conclusions survive a changed world. Model reasoning and deterministic runtime authority belong on opposite sides of a strict validation boundary.

## Next steps

- Add more enterprise event types without changing propagation logic.
- Connect real approval, policy, and document systems.
- Add Agent Registry/Gateway and Model Armor only where they strengthen—not destabilize—the P0 story.
- Benchmark avoided work and latency against restart-all orchestration.
