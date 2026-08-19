# 05 — Gemini Reasoning Protocol

## Principle

Gemini should reason semantically but operate under a narrow structured contract.

Do not ask Gemini to mutate state, invent source IDs, or decide whether a prior runtime Decision is stale.

## Reasoner responsibilities

1. Inspect allowed source fragments through read-only tools.
2. Produce a proposed outcome.
3. Break the outcome into atomic auditable claims.
4. Cite dependencies using only tool-returned stable refs.
5. Mark dependency materiality.
6. Identify unresolved blocking questions.
7. Provide a concise rationale summary.

## Prompt contract

The system instruction must state:

- source refs are opaque canonical identifiers;
- never fabricate refs;
- `proposed_outcome` must equal one of the request's explicit outcome options;
- every critical claim must cite at least one source or derived claim;
- policy/rule claims should cite exact policy fragments when available;
- distinguish facts from assessments;
- report contradictions explicitly;
- return only schema-conformant output;
- do not include hidden reasoning traces.

## Tool design

Suggested tools:

```text
search_source_catalog(query, filters)
get_fragment(fragment_ref)
get_structured_field(fragment_ref)
list_current_revisions(artifact_ids)
get_decision_context()
```

Tools return both content and stable refs. The model is never asked to generate a ref from a human-readable filename.

## Two-pass reasoning

### Pass A — Primary reasoner

Produces `DecisionDraft`.

### Pass B — Dependency critic

Receives:

- task definition;
- outcome and claims;
- proposed dependency set;
- source inventory summaries;
- selected source fragments.

It answers only:

```text
missing_material_dependencies
irrelevant_dependencies
possible_contradictions
unsupported_claims
```

The critic does not directly edit canonical state.

## Model diversity

P0 can use the same Gemini model with separate prompts. If budget allows, compare:

- primary reasoner = Gemini Flash;
- critic = higher-reasoning Gemini model.

The architecture must not depend on a specific model tier.

## Failure handling

### Invalid JSON/schema

Retry once with schema error feedback. Then reject.

An outcome outside the request's explicit option set follows the same bounded correction path. The request supplies the complete option vocabulary, never the benchmark's expected answer.

### Unknown references

Do not auto-correct by fuzzy matching. Reject or require explicit repair.

### Missing critical dependency

Set compilation status to `NEEDS_HUMAN_REVIEW` or `REJECTED_INCOMPLETE_DEPENDENCIES` based on policy.

### Contradictory evidence

Do not let the model silently choose a favorite source. Persist a contradiction finding and block high-risk approval unless a precedence rule exists.

## Live-evaluation requirement

At least one benchmark suite must call live Gemini. Fake executors are useful for unit tests but cannot satisfy module acceptance.
