# 07 — Completeness and Contradiction Checking

## Why referential validity is not enough

A perfectly valid dependency list can still be dangerously incomplete.

Example:

```text
Decision: approve access
Dependencies: manager approval
```

If the real rule also requires security training, all references may be valid while the decision is still unsafe.

## Completeness critic

The critic sees enough context to ask:

> Given this task, outcome, claims, and source inventory, what material dependency appears missing?

It must output structured findings.

```json
{
  "missing_dependencies": [
    {
      "candidate_ref": "access-policy@v5#section/training",
      "severity": "CRITICAL",
      "why": "Approval requires current security training"
    }
  ],
  "unsupported_claims": [],
  "irrelevant_dependencies": []
}
```

## Candidate-ref constraint

The critic must select from the existing source catalog or say `UNKNOWN_SOURCE_REQUIRED`. It cannot invent canonical refs.

## Completeness policy

Suggested P0 policy:

- any `CRITICAL` missing dependency => block acceptance;
- `SUPPORTING` omission => warning;
- `CONTEXTUAL` omission => ignore for validity.

## Contradiction model

Represent contradiction as first-class compiler finding:

```text
finding_id
claim_or_topic
source_ref_a
source_ref_b
severity
precedence_rule_applied?
resolution
```

## Deterministic precedence rules

Where possible, use domain-configured precedence before model judgment:

- newer policy revision supersedes older policy revision;
- signed human approval supersedes draft approval;
- canonical database record supersedes cached tool snapshot;
- mission-specific policy may override global policy if explicitly configured.

## Unresolved contradictions

If no precedence rule exists and the contradiction is material:

```text
status = NEEDS_HUMAN_REVIEW
```

Do not average confidence scores.

## Optional entailment checker

For critical source→claim edges, a small second-pass verifier can classify:

```text
SUPPORTED
PARTIALLY_SUPPORTED
NOT_SUPPORTED
AMBIGUOUS
```

This is an evaluation aid and guardrail, not proof of truth.

## Benchmark importance

Completeness checking must be evaluated on deliberate omission cases. Without omission tests, the system only proves it can reject hallucinated IDs — the easy part.
