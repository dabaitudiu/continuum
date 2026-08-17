# 16 — Test and Evaluation Plan

## Test philosophy

The most important tests are not LLM quality tests. They are semantic correctness tests around invalidation, commitments, and side effects.

## Unit tests

### Decision invalidation

Given seed graph and policy v12->v13:

- D42 stale.
- D50 stale.
- D43 remains valid.
- activation action blocked.

### Commitment matching

- wrong vendor document does not satisfy commitment;
- correct penetration-test event satisfies once;
- duplicate event does not trigger twice.

### Side-effect idempotency

- retry after committed action returns recorded result;
- duplicate activation does not create new simulator record.

### State transitions

Reject illegal transitions, e.g. `COMPLETED -> RUNNING` without reset/new mission.

## Integration tests

1. Start mission -> security decision stored with dependencies.
2. Policy change -> invalidation event produced.
3. Revalidation -> new commitment created.
4. Document upload -> commitment satisfies and revalidation resumes.
5. New decision supersedes old decision.
6. Procurement resumes only after required decisions are valid.
7. Vendor reaches ACTIVE.

## Fault injection tests

- kill/terminate worker between intent and commit;
- deliver duplicate Pub/Sub event;
- return transient tool failure;
- submit malformed agent dependency output;
- revoke/alter mock permission version.

## Agent quality eval

Create fixed fixtures:

- v12 policy + SOC2 -> approve.
- v13 + missing pen test -> require evidence, not approve.
- v13 + valid pen test -> approve.

Evaluate structured output validity and dependency recall.

## Demo acceptance test

A fresh seeded environment must complete the exact demo flow three consecutive times without manual database edits.
