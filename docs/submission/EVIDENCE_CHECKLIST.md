# Submission evidence checklist

`PASS` means direct evidence exists. `BLOCKED` means it requires an authenticated, billing-enabled Google Cloud project. No local fake is accepted as cloud proof.

| Evidence | Status | Authoritative proof |
|---|---|---|
| 36-hour falsification gate | PASS | [`../reports/36h-gate-report.md`](../reports/36h-gate-report.md) |
| Deterministic invalidation and D43 preservation | PASS | Domain tests plus Mission Control Chromium E2E |
| Durable SQLite restart recovery | PASS | `backend/tests/test_runtime_restart_api.py` |
| Browser reload preserves open Commitment | PASS | `frontend/e2e/mission-control.spec.ts` |
| Mission history can reopen a completed Mission | PASS | `frontend/e2e/mission-control.spec.ts` |
| Full hosted-runner CI | PASS | [Successful GitHub Actions run 32123929626](https://github.com/dabaitudiu/continuum/actions/runs/32123929626) |
| Architecture diagram | PASS | [`ARCHITECTURE.md`](ARCHITECTURE.md) |
| Policy-drift provenance product shot | PASS | [`assets/continuum-policy-drift-provenance.png`](assets/continuum-policy-drift-provenance.png) |
| Four-minute recording script | PASS | [`DEMO_SCRIPT.md`](DEMO_SCRIPT.md) |
| Devpost-style text draft | PASS | [`SUBMISSION_DRAFT.md`](SUBMISSION_DRAFT.md) |
| Live Gemini/ADK reasoning | BLOCKED | Requires Google credentials and captured `GOOGLE_ADK_GEMINI` run |
| Live Firestore persistence | BLOCKED | Requires deployed Mission documents in the target project |
| Live Pub/Sub delivery | BLOCKED | Requires deployed topic and published outbox evidence |
| Live Cloud Trace | BLOCKED | Requires trace explorer evidence from deployed requests |
| Public hosted UI | BLOCKED | Requires Cloud Run deployment URL |
| Three consecutive cloud runs | BLOCKED | Run `CONTINUUM_EXPECT_CLOUD=1 ./scripts/verify-deployment.sh CLOUD_RUN_URL 3` |
| Public demo video | BLOCKED | Record only after the cloud release gate passes |

## Final evidence capture

1. Save the Cloud Run URL in `SUBMISSION_DRAFT.md`.
2. Save one health response showing `google_adk`, `firestore`, `pubsub`, and `google_cloud_trace`.
3. Save three verifier lines, each with a distinct Mission ID and `mode=GOOGLE_ADK_GEMINI`.
4. Capture one Firestore Mission, one Pub/Sub message, and one correlated Cloud Trace.
5. Record the four-minute script and replace `PENDING_PUBLIC_VIDEO_URL`.
