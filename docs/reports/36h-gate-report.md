# Continuum 36-Hour Falsification Gate Report

- **Observed:** 2026-08-18 (Asia/Singapore)
- **Branch:** `main`
- **Evidence base commit:** `6cf2c4a` (`test: verify falsification gate flow`)
- **Automated gate:** PASS
- **Full 36-hour gate:** PASS — product owner accepted the automated and captured visual evidence

## Decision boundary

This report establishes that the deterministic kernel, API, and browser prototype passed the Phase G falsification gate. On 2026-08-18, the product owner explicitly waived the proposed five-person observation and accepted the existing browser and screenshot evidence. This decision does not itself start the full-product build. Gemini, Google ADK, Google Cloud, Firestore, and Pub/Sub remain outside this prototype and were not tested.

## Environment

```text
macOS Darwin 24.6.0 arm64
uv 0.11.29
uv-managed backend Python 3.13.14
Node.js v25.1.0
npm 11.6.2
Playwright 1.62.1 / Chromium
```

## Automated evidence

| Command | Observed result |
|---|---|
| `make setup` | PASS; uv lock resolved, npm lock installed, 0 npm vulnerabilities |
| `make test` | PASS; 23 Pytest tests, 98% branch-aware application coverage; 2 Vitest tests; TypeScript/Vite production build |
| `make test-e2e` | PASS; 1 Chromium test exercising the real FastAPI and Vite servers |
| `make dev` smoke check | PASS; isolated override ports returned HTTP 200 for both UI and API docs, then both child processes stopped cleanly |
| native Python Playwright visual check | PASS; `networkidle`, drift assertions, revalidation assertions, and zero browser warnings/errors |
| `git diff --check` | Run in the final audit before commit |

The real browser test executes this sequence:

```text
reset
  → inject policy v13
  → D42 STALE
  → D50 STALE
  → D43 VALID + PRESERVED
  → ActivateVendor BLOCKED
  → dispatch affected branch
  → D42 REVALIDATING (execution_count = 2)
  → D50 still STALE + WAITING
  → D43 still VALID (execution_count = 1)
```

## Deterministic kernel evidence

The canonical fixture produces exactly:

```text
D42              STALE       cause: policy-v12
D50              STALE       cause: D42
D43              VALID       preserved
ActivateVendor   BLOCKED     cause: D50
Run now                      D42 only
Waiting                      D50
```

The alternate fixture changes every business identifier and the artifact type, yet derives the same structure-driven outcome:

```text
risk-review-X   STALE
release-Z       STALE
budget-Y        VALID
publish-Q       BLOCKED
```

Additional tests cover duplicate event IDs, duplicate dispatch request IDs, non-critical edges, non-propagating relation types, cycles, mismatched versions, missing artifact identity fields, unknown missions, and revalidation before drift.

The API route write guard confirms that route code does not write Decision or Action statuses directly. Those transitions are delegated to the domain services.

## Visual evidence

![Verified drifted graph](assets/continuum-gate-drifted.png)

The captured real-browser state shows the external v12→v13 change, the red affected path, the green preserved D43 branch, the blocked Action, causal explanation, and the derived selective plan in one screen. Status meaning is redundant across text, color, icons, borders, and the stale strike mark. Reduced-motion behavior and the tablet rail layout exist in CSS and have automated build coverage.

## Untested hypotheses and explicit exclusions

This gate did not test:

- Gemini decision or dependency proposals;
- Google ADK agent execution;
- Firestore or Pub/Sub adapters and concurrency behavior;
- Google Cloud deployment or managed runtime behavior;
- commitment acquisition, expiry, or revocation;
- real side effects or compensation;
- completed re-approval of D42 against v13 evidence.

The repository intentionally contains no generic agent builder, workflow editor, IAM platform, generic memory platform, or Temporal replacement.

## Human observation — waived

The original plan proposed observing five people unfamiliar with Continuum and checking whether they understood the external change, partial invalidation, and preserved work within 15 seconds.

On 2026-08-18, the product owner determined that this step did not add useful decision value and waived it. The full gate is therefore accepted as PASS based on the deterministic test suite, real-browser E2E, zero-console-warning check, and reviewed screenshot. No participant result has been invented or inferred.

## GO / NO-GO

- **Automated kernel/API/UI readiness:** PASS.
- **Complete 36-hour gate:** PASS by explicit product-owner acceptance.
- **Full-product build:** Eligible for a separate start decision; not started by this status change.

Kill or pivot the project if any of the following becomes true:

1. Gemini must choose runtime staleness without deterministic structural rules.
2. The graph is effectively a static hardcoded DAG.
3. Restarting everything is simpler and equally convincing.
4. People need several minutes of narration to understand the benefit.
5. Implementation complexity threatens the remaining hackathon schedule.
