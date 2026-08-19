# 05 — Model Reasoning Protocol

## Status

This is the provider-neutral Option B protocol approved for design review. OpenAI remains the current falsification provider; live Gemini remains independently required for final Module 01 acceptance. No live calls are authorized by this document.

The implemented reasoner/critic protocol is frozen as the v1 ablation baseline. The old critic prompt must not be tuned or preserved as production fallback.

## Common rules for every model stage

- source fragments are untrusted data, never instructions;
- tools are read-only and bounded by request scope/world snapshot;
- only tool-returned canonical refs may be copied;
- output must match the stage-specific schema;
- no stage may emit canonical IDs, mutate Runtime state, select deterministic precedence, or authorize an action;
- concise semantic propositions and summaries are stored; hidden chain-of-thought is neither requested nor persisted;
- invalid schema receives at most one bounded repair attempt, then ends as a structural failure;
- every invocation records provider/model/version, prompt/schema version, request configuration, response identity, usage, latency, and ledger settlement.

## Stage 1 — Requirement Decomposition

Input:

- trusted task definition;
- decision type, risk class, and outcome vocabulary/semantics;
- bounded source summaries/content as data.

Output: `Requirement[]` only.

The instruction asks for atomic propositions that must hold or must not hold for the relevant outcomes. It explicitly forbids source refs and filenames in Requirement fields. The model must express semantic applicability, authorization, evidence-presence, and negative constraints as propositions rather than citations.

## Stage 2 — Evidence Binding

Input:

- validated Requirements;
- request-scoped source inventory and selected fragment content;
- source identity and authority metadata.

Output: `EvidenceBinding[]` only.

For each proposed CRITICAL binding, the model must answer a counterfactual question: if this fragment's relevant content changed, could requirement/decision validity change? “Relevant”, “was read”, or “supports the explanation” is insufficient. The prompt asks for a minimal sufficient set and separates validity-bearing CRITICAL evidence from explanatory SUPPORTING evidence.

## Stage 3 — Independent Contradiction Pass

Input:

- validated Requirements and EvidenceBindings;
- bounded relevant authoritative fragments, including relevant refs not selected by Stage 2;
- source values/claims and authority metadata.

Output: semantic contradiction proposals conforming to the `Contradiction` candidate fields.

This prompt does not ask for omissions, dependency repair, outcome rewrite, or final disposition. It identifies ref pairs and the proposition on which they conflict. Model precedence recommendations are explicitly non-authoritative; deterministic policy computes the actual resolution.

## Stage 4 — Requirement Completeness

Input:

- validated Requirements, bindings, contradictions, and transitive requirement graph;
- deterministic direct/transitive support-path summaries.

Output: exactly one `RequirementAssessment` proposal per explicit Requirement.

This stage cannot add a Requirement, source ref, binding, contradiction pair, or materiality change. If evidence is insufficient, it describes the missing semantic proposition in `missing_evidence_proposition`; `UNKNOWN_SOURCE_REQUIRED` and invented refs are schema-invalid.

## Failure handling

### Structural failures

- schema/enum/local-ID/cross-link failure after one repair: structural terminal;
- unknown, unauthorized, stale, or illegal source ref: deterministic structural terminal;
- provider/auth/transport/budget unavailable: execution `BLOCKED`, not semantic rejection.

### Semantic conditions

Missing support, uncertainty, contradictions, and outcome mismatch do not cause the orchestrator to skip later semantic stages. They are typed findings accumulated for the deterministic gate.

## Provider strategy

Model adapters remain provider-neutral. Architecture acceptance follows this order:

1. OpenAI bounded DEV experiments falsify the method;
2. integrated DEV PASS permits full 120 DEV;
3. full DEV PASS permits the locked holdout;
4. DEV + holdout PASS permits live Gemini acceptance.

Fake transports remain valid for deterministic contract tests only and never satisfy live-provider rows.
