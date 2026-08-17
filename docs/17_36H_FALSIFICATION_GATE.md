# 17 — 36-Hour Falsification Gate

Do not build the full product until this gate passes.

## Question being tested

Is semantic revalidation both technically real and visually compelling enough to justify the project?

## Prototype scope

No Gemini required for the first deterministic kernel proof.

Build only:

1. in-memory or Firestore graph entities;
2. seed decisions D42/D43/D50;
3. policy v12 artifact;
4. policy v13 supersession event;
5. deterministic invalidation propagation;
6. minimal graph visualization.

## Seed graph

```text
Policy v12 ----> D42 SecurityApproved ----> D50 ProcurementApproved ----> ActivateVendor
SOC2 A31 ------> D42
Financial F7 --> D43 FinancialApproved ----> D50
```

## Trigger

Create v13 and emit `policy.version.changed`.

## Required result

```text
D42 = STALE
D50 = STALE
ActivateVendor = BLOCKED
D43 = VALID
```

## Visual gate

A person unfamiliar with the project should understand in under 15 seconds that:

- something external changed;
- only a portion of previous work became invalid;
- unaffected work was preserved.

### Product-owner acceptance

On 2026-08-18, the product owner waived live participant observation for this hackathon gate and accepted the verified Chromium E2E flow plus the captured drifted-state screenshot as sufficient visual evidence. No participant observations are claimed or fabricated.

## PASS

Proceed if:

- invalidation is deterministic and tested;
- affected subgraph is obvious in UI;
- selective rerun can be explained in one sentence;
- implementation does not require hardcoding the exact demo node IDs into propagation logic.

## FAIL / PIVOT

Stop or rethink if:

- Gemini must decide which nodes turn stale at runtime with no structural rules;
- the graph is basically a static hardcoded DAG;
- "restart everything" is simpler and equally convincing;
- UI needs several minutes of narration to explain the benefit;
- implementation complexity threatens the rest of the hackathon schedule.
