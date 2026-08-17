# 22 — Acceptance Matrix

| Requirement | Automated proof | Demo proof |
|---|---|---|
| Mission persists | repository/state test | reload browser and state remains |
| Decision provenance | schema/reference tests | click decision and inspect evidence/policy |
| Policy drift invalidates D42 | unit test | v12->v13 graph transition |
| D43 remains valid | unit test | unaffected node visibly remains VALID |
| Downstream action blocked | unit/integration test | activation blocked after drift |
| Selective revalidation | integration test | only Security branch reruns |
| Commitment survives wait | integration test | pending pen-test commitment visible |
| Correct event wakes mission | event test | upload pen test resumes Security Agent |
| Duplicate event ignored | idempotency test | no duplicate work item |
| Side effect exactly-once behavior | ledger test | no duplicate email/activation |
| Gemini used materially | agent eval fixture | policy/document reasoning shown |
| ADK used | build/runtime inspection | deployed agent evidence |
| Google Cloud deployed | smoke test | Cloud console/trace/runtime shot |
| Observability | trace assertion/manual | trace spans/logs visible |
| Hosted UI works | browser E2E | judge can run demo scenario |
