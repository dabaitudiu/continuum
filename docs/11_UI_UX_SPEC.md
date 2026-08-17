# 11 — UI / UX Specification

## Product feel

Enterprise mission control, not chatbot. Dense enough to feel operational, but the core causal story must remain obvious.

## Navigation

1. Missions
2. Mission Control
3. Decision Graph
4. Memory & Commitments
5. Audit / Trace
6. Fleet (optional combined view)

## Missions page

Columns/cards:

- mission name;
- status;
- age/demo elapsed time;
- active agents;
- open commitments;
- stale decisions;
- last event.

## Mission Control

Top hero:

- mission title;
- status badge;
- one-line current explanation;
- demo clock.

Main panels:

### Timeline

Chronological events with semantic icons:

- normal event;
- waiting;
- policy drift;
- invalidation;
- revalidation;
- side effect;
- completion.

### Agent Fleet

Each agent: `IDLE`, `RUNNING`, `WAITING`, `BLOCKED`, `REVALIDATING`.

### Pending Commitments

Open obligations with trigger and age.

### Current blockers

Explicitly state why the mission cannot progress.

## Decision Graph

This is the visual centerpiece.

Node types:

- artifact/evidence;
- decision;
- action.

Status styling must be distinguishable without relying only on color; include labels/icons.

Interaction:

- click node -> side panel with provenance;
- show version and hash for artifacts;
- show supersession chain;
- highlight affected subgraph after drift.

## Policy drift animation

When v13 arrives:

1. Policy node changes version.
2. Edge impact highlight travels to D42.
3. D42 becomes `STALE`.
4. Downstream nodes become stale/blocked.
5. Unaffected Financial Review stays explicitly `VALID`.

Avoid excessive animation; clarity beats spectacle.

## Audit page

Filter by:

- agent;
- event type;
- tool;
- decision;
- trace id.

Expose both domain audit event and Cloud trace link/id where available.
