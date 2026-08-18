# Mission Control Local Product Report

**Date:** 2026-08-18  
**Milestone:** B  
**Result:** PASS — complete browser-operated local product story

## What now works

- A fresh Acme Analytics Mission is created from the browser.
- Start produces valid Policy v12 authorization and waits on Procurement's external activation window.
- No penetration-test Commitment exists before Policy v13.
- The v12→v13 world event deterministically makes D42/D50 stale, preserves D43, blocks activation, cancels the obsolete activation wait, and schedules only Security revalidation.
- The deterministic local Security adapter produces a typed missing-evidence result and durable pen-test Commitment.
- The exact `vendor.document.uploaded` event satisfies the Commitment once.
- D57 supersedes D42; D58 supersedes D50; D43 stays valid and is reused.
- The Side Effect Ledger commits vendor activation once; Vendor becomes `ACTIVE`; Mission becomes `COMPLETED`.
- All simulator and runtime state survives SQLite persistence.
- Mission Control shows the semantic route, provenance explanation, open Commitment predicate, event history, and a secondary Decision Graph.
- Transient restore, command, and history failures can be retried without abandoning the current Mission; mutating retries reuse the original idempotency key.
- At the supported 320px minimum width, all view controls remain visible and the complete scenario is operable from the keyboard.

## Honest execution boundary

The current UI permanently discloses `LOCAL DETERMINISTIC`. No screen, audit event, or README text claims the local adapters are Gemini, Google ADK, Agent Runtime, Firestore, Pub/Sub, or OpenTelemetry. Those integrations remain Milestones C–E.

## Visual verification

- `docs/reports/assets/mission-control-policy-drift.png`
- `docs/reports/assets/mission-control-missing-evidence.png`
- `docs/reports/assets/mission-control-completed.png`

The real browser captures were compared to `mission-control-visual-benchmark.png`. They preserve its causal hierarchy while using code-rendered, accessible route elements rather than a bitmap or decorative mock.

## Automated evidence

- 215 backend domain/API/repository tests, including canonical scenario and control read-model tests, at 94% branch-aware coverage.
- 13 frontend behavior/model tests plus a successful TypeScript/Vite production build.
- Two Playwright Chromium end-to-end tests: the durable desktop story and the complete 320px keyboard story.
- `git diff --check`.

## Optional post-gate integrations

Google ADK/Gemini, Firestore, Pub/Sub, Cloud Trace, and Cloud Run adapters now exist and are locally contract-tested. They remain optional extensions to the credential-free local product until authenticated cloud evidence is captured. No live-cloud result is implied by this report.
