# 22 — Acceptance Matrix

`PASS` is part of the credential-free local product. `DEFERRED` is an optional post-gate integration and is not required to prove the current falsification thesis.

| Requirement | Current scope | Automated proof | Demo proof |
|---|---|---|---|
| Mission persists | PASS | repository/state test | reload browser and state remains |
| Decision provenance | PASS | schema/reference tests | click decision and inspect evidence/policy |
| Policy drift invalidates D42 | PASS | unit test | v12->v13 graph transition |
| D43 remains valid | PASS | unit test | unaffected node visibly remains VALID |
| Downstream action blocked | PASS | unit/integration test | activation blocked after drift |
| Selective revalidation | PASS | integration test | only Security branch reruns |
| Commitment survives wait | PASS | integration test | pending pen-test commitment visible |
| Correct event wakes mission | PASS | event test | upload pen test resumes Security Agent |
| Duplicate event ignored | PASS | idempotency test | no duplicate work item |
| Side effect exactly-once behavior | PASS | ledger test | no duplicate email/activation |
| Transient UI failure is recoverable | PASS | frontend retry/idempotency tests | retry preserves the active Mission and operation ID |
| Keyboard and minimum-width operation | PASS | Chromium 320px keyboard E2E | all four views remain visible; Mission Control completes with Enter and Compiler Lab has no page overflow |
| Exact compiler source identity | PASS | identity, registry, validator tests | Compiler Lab exposes full revision/representation/fragment refs |
| Typed compiler IR + deterministic hash | PASS | schema, pipeline, repeated-hash tests | claims and immutable compilation hash are visible |
| Missing/stale/unauthorized dependency rejection | PASS | compiler validation and API tests | blocked reference cases expose findings and no Runtime action |
| Material contradiction gate | PASS | precedence/contradiction tests | equal-rank conflict returns `NEEDS_HUMAN_REVIEW` |
| Runtime compiler acceptance boundary | PASS | revision/world/CAS/idempotency/capability tests | accepted fixture commits once and returns an audit-linked receipt |
| 120-case, three-domain dependency corpus | PASS | corpus/schema/distribution tests | benchmark report is committed |
| Deterministic full-pipeline reference metrics | PASS | reproducible benchmark runner | report shows 100% reference recall/precision/contradiction/determinism |
| Live OpenAI compiler evidence | BLOCKED | transport/budget contracts pass; no authenticated run | UI says key not configured; cumulative hard cap is $10 |
| Live Gemini compiler evidence | BLOCKED | ADK transport contracts pass; no authenticated run | UI says credentials not configured |
| Gemini used materially | DEFERRED | agent contract fixture only | requires authenticated live run |
| ADK used | DEFERRED | adapter inspection only | requires authenticated live run |
| Google Cloud deployed | DEFERRED | deployment-script contract test only | requires target cloud project |
| Observability | DEFERRED | local instrumentation test only | requires live Cloud Trace evidence |
| Hosted UI works | DEFERRED | local browser E2E only | requires public deployment URL |
