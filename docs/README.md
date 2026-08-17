# Continuum Design Pack

This package is the implementation contract for **Continuum**, a hackathon project for the **Fortified Enterprise Fleet** track, with the deepest investment in **Core Execution & State**.

## Product thesis

> A long-lived enterprise agent should not merely remember where it stopped. It must know whether the reasons that justified its previous decisions are still valid when the world changes.

Continuum adds **semantic continuity** to long-running agents: explicit decision provenance, dependency invalidation, commitment memory, safe side-effect handling, and selective revalidation.

## Important implementation principle

This package intentionally contains **no finished application code**. It is written so a Gemini-powered coding agent can implement the project without inventing product semantics.

The hackathon rules require the submitted product to use Gemini 3.5+ (or newer), a Google agent framework, and Google Cloud infrastructure. They do not require every source line to be authored by Gemini. We are nevertheless using a Gemini-first implementation workflow so that the contest build has a clean, reproducible implementation history.

## Recommended reading order

1. `00_PROJECT_BRIEF.md`
2. `01_PRODUCT_REQUIREMENTS.md`
3. `02_SCOPE_AND_NON_GOALS.md`
4. `03_SYSTEM_ARCHITECTURE.md`
5. `04_DOMAIN_MODEL.md`
6. `05_RUNTIME_SEMANTICS.md`
7. `06_DECISION_PROVENANCE_AND_INVALIDATION.md`
8. `07_COMMITMENT_MEMORY.md`
9. `08_SIDE_EFFECT_LEDGER.md`
10. `09_AGENTS_AND_TOOLS.md`
11. `10_ENTERPRISE_SIMULATOR.md`
12. `11_UI_UX_SPEC.md`
13. `12_API_AND_EVENT_CONTRACTS.md`
14. `13_DATA_AND_MEMORY_MODEL.md`
15. `14_SECURITY_AND_GOVERNANCE.md`
16. `15_OBSERVABILITY.md`
17. `16_TEST_AND_EVAL_PLAN.md`
18. `17_36H_FALSIFICATION_GATE.md`
19. `18_BUILD_PLAN.md`
20. `19_GEMINI_HANDOFF_PROMPTS.md`
21. `20_DEMO_AND_SUBMISSION.md`
22. `21_RISK_REGISTER_AND_KILL_CRITERIA.md`
23. `22_ACCEPTANCE_MATRIX.md`
24. `23_OFFICIAL_GOOGLE_REFERENCES.md`

`GEMINI.md` is the root operating instruction for the coding agent.

## Golden rule

If implementation convenience conflicts with the semantics in this package, **the semantics win**. Do not silently simplify the core thesis into "save state and resume later."
