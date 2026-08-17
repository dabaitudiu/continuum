# Continuum

## Rule
1. Always reply in Chinese 永远用中文回答（除了专业术语）

## Goal
Build a hackathon prototype for the Google All Things Agentic （read all_things_agentic_hackathon.md)
Fortified Enterprise Fleet track.

## Core thesis
Prevent long-running agents from blindly continuing based on
decisions whose assumptions are no longer valid.

## Read first
1. README.md
2. docs/00_PROJECT_BRIEF.md
3. docs/03_SYSTEM_ARCHITECTURE.md
4. docs/05_RUNTIME_SEMANTICS.md
5. docs/06_DECISION_PROVENANCE_AND_INVALIDATION.md
6. docs/17_36H_FALSIFICATION_GATE.md
7. docs/18_BUILD_PLAN.md

## Critical invariant
Gemini may propose decisions and dependencies.
The runtime owns deterministic invalidation and state transitions.

DO NOT reduce Semantic Resume to ordinary checkpoint/resume.

## Current phase
We have NOT committed to the full build.

First implement only the falsification prototype:
Policy v12 -> v13
D42 -> STALE
D43 -> VALID
downstream(D42) -> STALE
selective branch re-execution

Stop and report after the falsification gate.

## Non-goals
Do not build:
- generic agent builder
- workflow editor
- generic IAM
- generic memory platform
- Temporal replacement

## Implementation
Use:
- Gemini 3.5+
- Google ADK
- Google Cloud
- Firestore / PubSub as specified

## Working rules
- Read specs before changing architecture.
- Do not silently change product semantics to simplify implementation.
- Add tests for runtime state transitions.
- Keep docs consistent with implementation.