# 20 — Demo and Submission Plan

## Four-minute story

### 0:00–0:25 — Problem

"Agents can work for minutes today. Enterprises need them to work for weeks. But the world changes while they wait."

Show Continuum Mission Control, not slides for too long.

### 0:25–1:05 — Start mission

Start `Onboard Acme Analytics`.

Show three agents and initial security approval based on:

- Security Policy v12;
- SOC2 A31;
- Vendor Profile r7.

### 1:05–1:25 — Wait

Mission reaches waiting/approval state. Show open state/commitment if appropriate.

### 1:25–2:05 — Inject policy drift

Upgrade v12 -> v13.

Decision Graph visibly shows:

- D42 stale;
- D50 stale;
- activation blocked;
- D43 valid.

Say one sentence: "Continuum doesn't restart the mission; it invalidates only work whose assumptions changed."

### 2:05–2:45 — Revalidation + commitment

Security Agent wakes and reads v13. It determines penetration-test evidence is missing. A durable commitment appears.

### 2:45–3:15 — Time compression

Simulate seven days / upload penetration test. Event satisfies commitment. Security Agent revalidates, new decision supersedes old one.

### 3:15–3:35 — Complete

Procurement resumes and vendor becomes ACTIVE.

### 3:35–3:50 — Production proof

Show Google Cloud Agent Runtime / Cloud Run / trace/log view proving deployed backend execution.

### 3:50–4:00 — Close

> "Continuum doesn't just remember where an agent stopped. It remembers why it was allowed to continue."

## Optional crash-recovery shot

Only include if stable and time permits. Do not sacrifice the policy-drift story.

## Submission assets

- Hosted project URL.
- Repo URL.
- README spin-up instructions.
- Architecture diagram.
- Public YouTube/Vimeo demo in English or with English subtitles.
- Text write-up: problem, value, functionality, Google stack, findings/learning.

## Architecture diagram emphasis

Clearly separate:

1. Google Agent Platform capabilities.
2. Continuum semantic runtime.
3. Enterprise simulator.
4. Mission Control.
