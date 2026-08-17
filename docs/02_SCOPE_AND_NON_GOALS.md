# 02 — Scope and Non-Goals

## P0 — Must exist

1. Three ADK agents.
2. One vendor-onboarding mission template.
3. Persistent mission state.
4. Decision + evidence + dependency records.
5. Policy versioning.
6. Invalidation propagation.
7. Selective revalidation.
8. Commitment creation/matching.
9. Pub/Sub wakeup or equivalent cloud event path.
10. Side-effect ledger with one idempotent simulated external action.
11. Mission Control UI.
12. Decision Graph UI.
13. Google Cloud deployment.
14. OpenTelemetry traces.

## P1 — Strongly desirable

- Kill-worker recovery demonstration.
- Agent Registry registration.
- Agent Identity / IAM separation.
- Agent Gateway integration.
- Model Armor integration.
- Memory Bank for semantic long-term memory.

## P2 — Only if P0/P1 are solid

- Multiple mission templates.
- User-configurable policies.
- Multi-tenant separation.
- Compensation workflows.
- Complex graph editing.
- Analytics dashboard.

## Explicit non-goals

Do not build:

- a generic workflow designer;
- a drag-and-drop agent builder;
- a marketplace;
- a generic IAM product;
- a replacement for Temporal;
- a generic vector memory database;
- a complete procurement application;
- a complete security-compliance platform.

## Fleet coverage strategy

| Fleet capability | Depth | Continuum implementation |
|---|---:|---|
| Agent Registry | Light | Register the three deployed agents; show versions/capabilities |
| Agent Runtime | Deep | Long-lived mission semantics, revalidation, recovery |
| Memory Bank | Medium | Use Google Memory Bank for long-term semantic memory; custom commitment/decision state remains explicit |
| Agent Identity | Light/Medium | Separate agent principals/scopes where feasible |
| Agent Gateway | Light/Medium | Route governed tool traffic if available |
| Model Armor | Light | Protect external text/tool payloads if available |
| Observability | Medium/Deep | OTel trace + domain audit ledger |
