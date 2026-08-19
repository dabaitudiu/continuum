# Current Context for Module 01

## Existing spike

The current repository already proves:

- deterministic graph invalidation;
- selective revalidation planning;
- a durable local mission aggregate;
- commitments and side-effect ledger;
- a canonical vendor-onboarding browser scenario;
- preliminary ADK/Gemini wiring and Google Cloud adapters.

## Known limitation motivating this module

The full ACME scenario still predefines much of the semantic dependency graph and workflow outcome. Therefore the existing implementation does **not** yet prove that Continuum can derive dependable provenance from real model reasoning over messy enterprise sources.

## What Module 01 changes

After this module, a Security/Release/Access agent should be able to inspect versioned source fragments and propose a structured decision whose critical dependencies are validated and measured against a benchmark.

The Drift Engine should then consume canonical dependencies rather than hand-authored demo edges.

## Implementation state — 2026-08-19

- Phase A source identity is complete.
- Phases B–C implement typed IR, deterministic validation, canonicalization, exact source authorization, and compilation hashes.
- Phase D implements provider-neutral reasoner/critic contracts, OpenAI Responses transport with a persisted cumulative $10 hard budget, and Google ADK/Gemini transport. The authenticated OpenAI lane has completed; Gemini still has no authenticated evidence.
- Phase E implements failure-closed completeness, contradiction findings, authority precedence, and blocking dispositions.
- Phase F commits 120 schema-validated cases across vendor onboarding, production release, and privileged access, plus reproducible baselines, mutation evaluation, a balanced 30-case variance subset, and report generation.
- Phase G persists compilation aggregates in memory/SQLite/Firestore and accepts only immutable `ACCEPTED` results into Runtime under exact mission revision/world snapshot checks, idempotent inbox handling, audit linkage, and capability boundaries.
- Compiler Lab exposes exact sources, claim provenance, validation findings, compilation hashes, honest evidence-lane status, and an accepted reference Runtime receipt.

## Current limitation

The deterministic full-pipeline reference lane passes. The authenticated OpenAI lane completes all 120 primary cases and 90 variance observations but fails the quality gate: proposal-union recall is 0.9821, proposal precision 0.6548, accepted canonical recall 34/168, contradiction recall 0, outcome compliance 0.4250, and must-block compliance 0.2667. Its historical 0.8056 stale-escape value includes 58 NOT_ACCEPTED cases; corrected accepted-only Runtime evidence is 0/14 stale escapes and 0/6 unnecessary invalidations, but acceptance and supporting-ref mutation coverage are inadequate. The bounded 30-case paired ablation triggers K3 for the current critic: 0 omissions recovered, 0 contradictions detected, 4 false-positive refs, 5 spurious blocks, and acceptance reduced from 8 to 3. Its 38 settled calls cost $0.065727100. Live Gemini remains `BLOCKED` by absent credentials. K6 is not cleared and the module definition of done is not met; stop for product-owner review of critic removal/redesign before Experiment 2 or Module 02.
