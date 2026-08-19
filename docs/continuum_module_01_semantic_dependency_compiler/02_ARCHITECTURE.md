# 02 — Architecture

## Component topology

```text
                         ┌──────────────────────┐
                         │  Artifact Ingestion  │
                         └──────────┬───────────┘
                                    │
                         SourceRegistry / Index
                                    │
         ┌──────────────────────────┴────────────────────────┐
         │                                                   │
         v                                                   v
┌──────────────────┐                              ┌───────────────────┐
│ Bounded Tool API │                              │ Decision Request  │
└────────┬─────────┘                              └─────────┬─────────┘
         │                                                    │
         └──────────────────────┬─────────────────────────────┘
                                v
                     ┌─────────────────────┐
                     │ Gemini Reasoner     │
                     │ DecisionDraft       │
                     └──────────┬──────────┘
                                v
                     ┌─────────────────────┐
                     │ Schema Validator    │
                     └──────────┬──────────┘
                                v
                     ┌─────────────────────┐
                     │ Reference Validator │
                     └──────────┬──────────┘
                                v
                     ┌─────────────────────┐
                     │ Temporal/Scope Gate │
                     └──────────┬──────────┘
                                v
                     ┌─────────────────────┐
                     │ Completeness Critic │
                     └──────────┬──────────┘
                                v
                     ┌─────────────────────┐
                     │ Contradiction Gate  │
                     └──────────┬──────────┘
                                v
                     ┌─────────────────────┐
                     │ Canonicalizer       │
                     └──────────┬──────────┘
                                v
                       CompilationResult
                                │
                                v
                     Continuum Runtime API
```

## Trust boundaries

### Trusted deterministic boundary

- artifact IDs and revision IDs;
- fragment IDs;
- source access scope;
- canonical hashes;
- schema validation;
- reference existence;
- temporal validity;
- graph type rules;
- canonical ordering/deduplication;
- compiler status transitions.

### Probabilistic boundary

- meaning of policy text;
- claim extraction;
- relevance of evidence;
- proposed materiality;
- contradiction interpretation;
- omitted-dependency critique.

## Compiler stages

### Stage A — Context assembly

Build a bounded context package using read-only tools. The model never receives direct DB write access.

### Stage B — Decision drafting

Gemini emits typed `DecisionDraft` with claims, dependency refs, unresolved questions, and concise rationale.

### Stage C — Deterministic validation

Reject invalid IDs, unauthorized refs, wrong revisions, malformed relationships, impossible cycles where prohibited, and duplicate identities.

### Stage D — Completeness critique

A separate critic examines whether the proposed decision appears to omit material dependencies given the task and source inventory.

### Stage E — Contradiction analysis

Flag unresolved contradictory claims/sources. Contradictions are not silently averaged away.

### Stage F — Canonicalization

Normalize claims, edges, ordering, IDs, materiality, source versions, and content hashes into canonical graph mutations.

### Stage G — Compilation disposition

Possible results:

- `ACCEPTED`
- `NEEDS_HUMAN_REVIEW`
- `REJECTED_INVALID_REFERENCE`
- `REJECTED_STALE_SOURCE`
- `REJECTED_CONTRADICTION`
- `REJECTED_INCOMPLETE_DEPENDENCIES`
- `REJECTED_SCHEMA`

## Integration boundary

The module exposes a compiler service. The runtime may accept the compilation result and create a Decision, but only the runtime assigns final mission/decision lifecycle status.
