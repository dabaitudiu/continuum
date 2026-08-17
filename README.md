# Continuum

Continuum is a mission-control runtime concept for long-lived enterprise agents. It detects when the assumptions behind earlier AI decisions have become stale and selectively revalidates only the affected execution branches.

This repository is currently the canonical product and architecture handoff for a Google All Things Agentic hackathon prototype in the Fortified Enterprise Fleet track. The full product build has not started.

## Current gate

The next build is limited to the 36-hour falsification prototype:

```text
Policy v12 -> v13
D42 -> STALE
D43 -> VALID
downstream(D42) -> STALE
ActivateVendor -> BLOCKED
selective branch re-execution
```

Do not proceed to the full product until the deterministic and visual gate passes.

## Start here

1. Read [AGENTS.md](AGENTS.md).
2. Read the [design-pack index](docs/README.md).
3. Review the [36-hour falsification gate](docs/17_36H_FALSIFICATION_GATE.md).
4. Review the approved-for-review [Phase G design specification](docs/superpowers/specs/2026-08-17-falsification-gate-design.md).

## Core invariant

Gemini may propose decisions and dependencies. The Continuum runtime owns deterministic invalidation and canonical state transitions.

Semantic Resume is not ordinary checkpoint/resume.
