# 21 — Risk Register and Kill Criteria

## R1 — "This is just durable workflow"

Mitigation: never lead with crash recovery. Lead with policy/world drift invalidating old AI decisions.

Kill condition: demo value is still mainly save/resume/retry.

## R2 — Dependency graph is hardcoded

Mitigation: graph engine generic; agent produces references against real input artifacts.

Kill condition: adding another policy/document type requires editing propagation logic for specific node IDs.

## R3 — Gemini dependency extraction is unreliable

Mitigation:

- constrain candidate dependency IDs supplied to model;
- schema validation;
- reject unknown IDs;
- eval fixture coverage.

Kill condition: agent regularly emits ungrounded dependencies and manual cleanup is required during demo.

## R4 — Invalidating only a branch has no meaningful benefit

Mitigation: demo graph includes enough completed independent work to make preservation visually obvious.

Kill condition: restart-all is indistinguishable in cost/time/behavior for the demo.

## R5 — Enterprise Platform features consume build time

Mitigation: make Registry/Gateway/Model Armor/Identity P1 adapters. P0 is stable without them.

Kill condition: provisioning a Preview feature blocks the core demo for more than a bounded troubleshooting window.

## R6 — Too much infrastructure, weak product

Mitigation: Mission Control and Decision Graph by Phase 4/10, not at the end.

Kill condition: two days before submission the primary interaction is still terminal/logs.

## R7 — Fake long-running story

Mitigation: durable commitment + event wakeup are real; only wall-clock time is compressed.

Kill condition: "simulate 7 days" directly forces state transitions instead of emitting normal events.

## R8 — Side effects are unsafe

Mitigation: ledger + idempotency and block actions under stale decisions.

Kill condition: duplicate activation/email observed after retry.

## R9 — Google stack looks bolted on

Mitigation: deploy actual ADK/Gemini agents to Google Agent Runtime, use OTel and cloud event/state infrastructure naturally.

Kill condition: replacing Gemini/ADK with a mock would make the demo materially identical.

## Final GO criteria

GO only if:

- 36-hour gate passes;
- policy drift story works end-to-end;
- graph is visually legible;
- Gemini agents contribute real reasoning;
- P0 cloud deployment is stable;
- demo completes three consecutive times.
