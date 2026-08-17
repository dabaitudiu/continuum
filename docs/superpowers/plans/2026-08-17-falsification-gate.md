# Continuum Falsification Gate Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build and verify the 36-hour Phase G prototype that deterministically invalidates the Policy v12-dependent branch, preserves D43, blocks ActivateVendor, and dispatches only the runnable stale root.

**Architecture:** A Python 3.11+ domain kernel owns graph state, idempotent event handling, invalidation, and revalidation planning behind an in-memory repository. FastAPI exposes four gate endpoints. A Vite/React/TypeScript app consumes the API and renders the approved light Decision Graph with React Flow; no LLM or cloud infrastructure participates in canonical transitions.

**Tech Stack:** Python 3.11+, uv, FastAPI, Pydantic v2, pytest, httpx; Node.js 20+, npm, React, TypeScript, Vite, `@xyflow/react`, Vitest, Testing Library, Playwright.

**Spec:** `docs/superpowers/specs/2026-08-17-falsification-gate-design.md`

## Global Constraints

- Scope is Phase G only. Do not add Gemini, ADK, Firestore, Pub/Sub, commitments, side-effect execution, cloud deployment, or full Mission Control.
- The runtime alone mutates canonical statuses; API/demo controls only create world inputs and domain events.
- No invalidation or graph layout behavior may branch on D42, D43, D50, or ActivateVendor identifiers.
- Edge direction is always dependency/source → dependent/consumer.
- Required drifted state is D42 `STALE`, D50 `STALE`, ActivateVendor `BLOCKED`, D43 `VALID`.
- After dispatch, D42 becomes `REVALIDATING`; D50 remains `STALE`; D43 remains `VALID` with `execution_count == 1`.
- Duplicate event and revalidation request IDs are idempotent.
- UI uses the approved benchmark and token system; status is encoded with text/icon/shape, not color alone.
- TDD is mandatory: every production behavior begins with a test that is observed failing for the expected reason.
- Stop after gate verification and report. Do not advance into the full build.

---

## File Map

```text
backend/
  pyproject.toml                  Python dependencies and pytest configuration
  app/__init__.py                 Package marker
  app/main.py                     FastAPI app factory and four endpoint contracts
  app/domain/models.py            Graph-domain enums and validated API/domain records
  app/domain/invalidation.py      Deterministic direct + downstream invalidation
  app/domain/revalidation.py      Minimal plan derivation and idempotent stub dispatch
  app/repository/protocol.py      Repository Protocol used by services
  app/repository/memory.py        In-memory graph and processed-request storage
  app/demo/fixture.py             Canonical and alternate non-ID-coupled fixtures
  tests/test_fixture.py           Initial-state and repository behavior
  tests/test_invalidation.py      Exact, generic, edge, cycle, and event-idempotency proof
  tests/test_revalidation.py      Runnable/waiting/retained plan and dispatch proof
  tests/test_api.py               Four endpoint contracts and demo-control safety
frontend/
  package.json                    UI scripts and dependencies
  tsconfig.json                   Strict TypeScript config
  vite.config.ts                  Vite/Vitest configuration and backend proxy
  index.html                      Vite entry document
  src/main.tsx                    React bootstrap
  src/App.tsx                     Gate screen state and commands
  src/api.ts                      Typed HTTP client
  src/types.ts                    API DTOs shared by UI modules
  src/graph-model.ts              API graph → React Flow elements
  src/components/DecisionGraph.tsx Graph canvas and custom nodes
  src/components/ProvenancePanel.tsx Cause and revalidation plan
  src/components/EventLog.tsx     Compact domain event footer
  src/styles.css                  Approved token system and responsive states
  src/test/setup.ts               DOM/ResizeObserver test setup
  src/graph-model.test.ts         Pure graph transformation behavior
  src/App.test.tsx                User-visible drift and dispatch behavior
  e2e/gate.spec.ts                Browser contract for reset → drift → revalidate
scripts/dev.sh                    Starts backend and frontend with cleanup traps
Makefile                          setup/test/dev commands
README.md                         Local gate run and verification instructions
docs/reports/36h-gate-report.md   Automated evidence and pending human visual test
```

---

### Task 1: Backend Scaffold, Models, Repository, and Fixtures

**Files:**
- Create: `backend/pyproject.toml`
- Create: `backend/app/__init__.py`
- Create: `backend/app/domain/__init__.py`
- Create: `backend/app/domain/models.py`
- Create: `backend/app/repository/__init__.py`
- Create: `backend/app/repository/protocol.py`
- Create: `backend/app/repository/memory.py`
- Create: `backend/app/demo/__init__.py`
- Create: `backend/app/demo/fixture.py`
- Test: `backend/tests/test_fixture.py`

**Interfaces:**
- Produces: `GraphSnapshot`, `WorldArtifact`, `EvidenceNode`, `DecisionNode`, `ActionNode`, `DependencyEdge`, `DomainEvent`, `RevalidationPlan`, `DispatchRecord`.
- Produces: `GraphRepository` Protocol and `InMemoryGraphRepository`.
- Produces: `seed_canonical_mission(repo) -> str` and `seed_alternate_mission(repo) -> tuple[str, DomainEvent]`.

- [ ] **Step 1: Create Python test configuration**

Create `backend/pyproject.toml`:

```toml
[project]
name = "continuum-gate"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = [
  "fastapi>=0.115",
  "pydantic>=2.10",
  "uvicorn[standard]>=0.34",
]

[dependency-groups]
dev = [
  "httpx>=0.28",
  "pytest>=8.3",
  "pytest-cov>=6.0",
]

[tool.pytest.ini_options]
testpaths = ["tests"]
addopts = "-q --strict-markers"
```

- [ ] **Step 2: Write the failing canonical-fixture test**

Create `backend/tests/test_fixture.py`:

```python
from app.demo.fixture import seed_canonical_mission
from app.domain.models import ActionStatus, DecisionStatus
from app.repository.memory import InMemoryGraphRepository


def test_canonical_fixture_starts_current_valid_and_ready() -> None:
    repo = InMemoryGraphRepository()
    mission_id = seed_canonical_mission(repo)

    snapshot = repo.get_snapshot(mission_id)

    assert snapshot.artifacts["policy-v12"].status.value == "CURRENT"
    assert {node_id: node.status for node_id, node in snapshot.decisions.items()} == {
        "D42": DecisionStatus.VALID,
        "D43": DecisionStatus.VALID,
        "D50": DecisionStatus.VALID,
    }
    assert snapshot.actions["activate-vendor"].status is ActionStatus.READY
    assert {node_id: node.execution_count for node_id, node in snapshot.decisions.items()} == {
        "D42": 1,
        "D43": 1,
        "D50": 1,
    }
    assert len(snapshot.edges) == 6
```

Production mutation caught: an incorrect initial status, missing graph edge, or wrong execution count.

- [ ] **Step 3: Run the test and verify RED**

Run:

```bash
cd backend && uv run --group dev pytest tests/test_fixture.py -v
```

Expected: collection fails because `app.demo.fixture` and the domain/repository modules do not exist.

- [ ] **Step 4: Implement minimal typed models and repository**

Implement Pydantic string enums and models in `models.py`. `GraphSnapshot` owns dictionaries keyed by node ID plus `edges`, `events`, and `dispatches`. Add `model_copy(deep=True)` at repository boundaries so callers cannot mutate storage by reference.

Required `GraphRepository` Protocol methods and exact signatures:

- `create_snapshot(self, snapshot: GraphSnapshot) -> None`
- `get_snapshot(self, mission_id: str) -> GraphSnapshot`
- `save_snapshot(self, snapshot: GraphSnapshot) -> None`
- `has_processed_event(self, mission_id: str, event_id: str) -> bool`
- `mark_event_processed(self, mission_id: str, event_id: str) -> None`
- `has_processed_request(self, mission_id: str, request_id: str) -> bool`
- `mark_request_processed(self, mission_id: str, request_id: str) -> None`

The fixture must declare edges from source to dependent using these relations:

```text
policy-v12 -> D42              GOVERNED_BY critical
soc2-A31 -> D42               SUPPORTED_BY critical
financial-F7 -> D43           SUPPORTED_BY critical
D42 -> D50                    REQUIRES critical
D43 -> D50                    REQUIRES critical
D50 -> activate-vendor        AUTHORIZES critical
```

Use stable edge IDs `policy-D42`, `soc2-D42`, `financial-D43`, `D42-D50`, `D43-D50`, and `D50-activate` so tests can mutate relation metadata without depending on list position.

- [ ] **Step 5: Run fixture tests and verify GREEN**

Run:

```bash
cd backend && uv run --group dev pytest tests/test_fixture.py -v
```

Expected: 1 passed.

- [ ] **Step 6: Commit Task 1**

```bash
git add backend
git commit -m "feat: seed gate domain graph"
```

---

### Task 2: Deterministic Invalidation Kernel

**Files:**
- Create: `backend/app/domain/invalidation.py`
- Modify: `backend/app/demo/fixture.py`
- Test: `backend/tests/test_invalidation.py`

**Interfaces:**
- Consumes: `GraphRepository`, `DomainEvent`, graph-domain models.
- Produces: `InvalidationService.process_artifact_change(mission_id: str, event: DomainEvent) -> GraphSnapshot`.

- [x] **Step 1: Write the failing exact-gate and genericity tests**

Create `backend/tests/test_invalidation.py` with literal expectations:

```python
from copy import deepcopy

import pytest

from app.demo.fixture import seed_alternate_mission, seed_canonical_mission
from app.domain.invalidation import InvalidationService
from app.domain.models import (
    ActionStatus,
    ArtifactStatus,
    DecisionStatus,
    DependencyEdge,
    DomainEvent,
    RelationType,
)
from app.repository.memory import InMemoryGraphRepository


def policy_v13_event(event_id: str = "evt-1") -> DomainEvent:
    return DomainEvent(
        event_id=event_id,
        event_type="policy.version.changed",
        payload={
            "logical_key": "security-policy",
            "old_artifact_id": "policy-v12",
            "new_artifact_id": "policy-v13",
            "old_version": "v12",
            "new_version": "v13",
        },
    )


def canonical_runtime() -> tuple[InMemoryGraphRepository, str, InvalidationService]:
    repo = InMemoryGraphRepository()
    mission_id = seed_canonical_mission(repo)
    return repo, mission_id, InvalidationService(repo)


def test_policy_v13_invalidates_only_security_dependent_branch() -> None:
    repo, mission_id, service = canonical_runtime()

    snapshot = service.process_artifact_change(mission_id, policy_v13_event("evt-1"))

    assert snapshot.decisions["D42"].status is DecisionStatus.STALE
    assert snapshot.decisions["D50"].status is DecisionStatus.STALE
    assert snapshot.decisions["D43"].status is DecisionStatus.VALID
    assert snapshot.actions["activate-vendor"].status is ActionStatus.BLOCKED
    assert snapshot.artifacts["policy-v12"].status is ArtifactStatus.SUPERSEDED
    assert snapshot.artifacts["policy-v13"].status is ArtifactStatus.CURRENT


def test_alternate_ids_and_artifact_type_use_same_rules() -> None:
    repo = InMemoryGraphRepository()
    mission_id, event = seed_alternate_mission(repo)

    snapshot = InvalidationService(repo).process_artifact_change(mission_id, event)

    assert snapshot.decisions["risk-review-X"].status is DecisionStatus.STALE
    assert snapshot.decisions["release-Z"].status is DecisionStatus.STALE
    assert snapshot.decisions["budget-Y"].status is DecisionStatus.VALID
    assert snapshot.actions["publish-Q"].status is ActionStatus.BLOCKED
```

Production mutations caught: any ID-specific branch, missing direct invalidation, missing propagation, or sibling over-invalidation.

- [x] **Step 2: Run targeted tests and verify RED**

```bash
cd backend && uv run --group dev pytest tests/test_invalidation.py -v
```

Expected: import failure for `InvalidationService`.

- [x] **Step 3: Implement direct invalidation and propagation**

Implement:

```python
DIRECT_INVALIDATION_RELATIONS = {
    RelationType.GOVERNED_BY,
    RelationType.SUPPORTED_BY,
    RelationType.DERIVED_FROM,
    RelationType.REQUIRES,
}
DECISION_PROPAGATION_RELATIONS = {
    RelationType.REQUIRES,
    RelationType.DERIVED_FROM,
}
```

The algorithm must:

1. Return the stored snapshot unchanged for a processed event ID.
2. Validate that old/new artifact IDs and versions in the event match stored artifacts.
3. Add the new artifact, mark the old artifact superseded, then find critical outgoing edges from the old artifact.
4. Mark directly affected Decisions stale.
5. Breadth-first traverse critical outgoing edges with a visited set.
6. Mark dependent Decisions stale only for decision propagation relations.
7. Mark dependent Actions blocked only for `AUTHORIZES`.
8. Append one event record and persist once.

- [x] **Step 4: Add edge, cycle, and idempotency RED tests**

Add tests proving:

```python
def test_noncritical_edge_does_not_propagate() -> None:
    repo, mission_id, service = canonical_runtime()
    snapshot = repo.get_snapshot(mission_id)
    edge = next(edge for edge in snapshot.edges if edge.edge_id == "D42-D50")
    edge.critical = False
    repo.save_snapshot(snapshot)

    result = service.process_artifact_change(mission_id, policy_v13_event())

    assert result.decisions["D42"].status is DecisionStatus.STALE
    assert result.decisions["D50"].status is DecisionStatus.VALID
    assert result.actions["activate-vendor"].status is ActionStatus.READY


def test_non_validity_relation_does_not_propagate() -> None:
    repo, mission_id, service = canonical_runtime()
    snapshot = repo.get_snapshot(mission_id)
    edge = next(edge for edge in snapshot.edges if edge.edge_id == "D42-D50")
    edge.relation_type = RelationType.SUPPORTED_BY
    repo.save_snapshot(snapshot)

    result = service.process_artifact_change(mission_id, policy_v13_event())

    assert result.decisions["D42"].status is DecisionStatus.STALE
    assert result.decisions["D50"].status is DecisionStatus.VALID


def test_cycle_terminates_and_invalidates_each_reachable_decision() -> None:
    repo, mission_id, service = canonical_runtime()
    snapshot = repo.get_snapshot(mission_id)
    snapshot.edges.append(
        DependencyEdge(
            edge_id="D50-D42-cycle",
            from_node_id="D50",
            to_node_id="D42",
            relation_type=RelationType.REQUIRES,
            critical=True,
        )
    )
    repo.save_snapshot(snapshot)

    result = service.process_artifact_change(mission_id, policy_v13_event())

    assert result.decisions["D42"].status is DecisionStatus.STALE
    assert result.decisions["D50"].status is DecisionStatus.STALE
    assert len(result.events) == 1


def test_duplicate_event_returns_same_state_without_new_event() -> None:
    repo, mission_id, service = canonical_runtime()
    first = service.process_artifact_change(mission_id, policy_v13_event("evt-duplicate"))

    second = service.process_artifact_change(mission_id, policy_v13_event("evt-duplicate"))

    assert second == first
    assert len(second.events) == 1


def test_mismatched_artifact_version_is_rejected_without_mutation() -> None:
    repo, mission_id, service = canonical_runtime()
    before = deepcopy(repo.get_snapshot(mission_id))
    event = policy_v13_event()
    event.payload["old_version"] = "v11"

    with pytest.raises(ValueError, match="old artifact version"):
        service.process_artifact_change(mission_id, event)

    assert repo.get_snapshot(mission_id) == before
```

Each test asserts full observable statuses/event counts, not helper calls.

- [x] **Step 5: Run tests, complete minimal behavior, and verify GREEN**

```bash
cd backend && uv run --group dev pytest tests/test_invalidation.py -v
cd backend && uv run --group dev pytest -v
```

Expected: all backend tests pass with no warnings.

- [x] **Step 6: Commit Task 2**

```bash
git add backend/app/domain/invalidation.py backend/app/demo/fixture.py backend/tests/test_invalidation.py
git commit -m "feat: invalidate stale decision branches"
```

---

### Task 3: Revalidation Planner and Idempotent Stub Dispatch

**Files:**
- Create: `backend/app/domain/revalidation.py`
- Test: `backend/tests/test_revalidation.py`

**Interfaces:**
- Consumes: invalidated `GraphSnapshot` and `GraphRepository`.
- Produces: `RevalidationService.plan(mission_id: str) -> RevalidationPlan`.
- Produces: `RevalidationService.dispatch(mission_id: str, request_id: str) -> list[DispatchRecord]`.

At the top of `backend/tests/test_revalidation.py`, define the shared setup explicitly:

```python
def invalidated_canonical_runtime() -> tuple[InMemoryGraphRepository, str]:
    repo = InMemoryGraphRepository()
    mission_id = seed_canonical_mission(repo)
    InvalidationService(repo).process_artifact_change(
        mission_id,
        DomainEvent(
            event_id="evt-revalidation",
            event_type="policy.version.changed",
            payload={
                "logical_key": "security-policy",
                "old_artifact_id": "policy-v12",
                "new_artifact_id": "policy-v13",
                "old_version": "v12",
                "new_version": "v13",
            },
        ),
    )
    return repo, mission_id
```

- [x] **Step 1: Write the failing plan test**

```python
def test_plan_runs_stale_root_waits_on_stale_dependent_and_retains_valid_sibling() -> None:
    repo, mission_id = invalidated_canonical_runtime()

    plan = RevalidationService(repo).plan(mission_id)

    assert plan.stale_decision_ids == ["D42", "D50"]
    assert plan.runnable_decision_ids == ["D42"]
    assert plan.waiting_decision_ids == ["D50"]
    assert plan.blocked_action_ids == ["activate-vendor"]
    assert plan.retained_decision_ids == ["D43"]
    assert plan.cause_by_node_id == {
        "D42": "policy-v12",
        "D50": "D42",
        "activate-vendor": "D50",
    }
```

Production mutations caught: rerunning all decisions, dispatching a dependent before its stale prerequisite, or dropping causal explanation.

- [x] **Step 2: Run and verify RED**

```bash
cd backend && uv run --group dev pytest tests/test_revalidation.py::test_plan_runs_stale_root_waits_on_stale_dependent_and_retains_valid_sibling -v
```

Expected: import failure for `RevalidationService`.

- [x] **Step 3: Implement deterministic plan derivation**

Sort output IDs lexically for stable API/tests. A stale Decision is waiting if any incoming critical `REQUIRES`/`DERIVED_FROM` edge originates from a stale Decision; otherwise it is runnable. Retained Decisions are all valid Decisions not in the stale set.

- [x] **Step 4: Write the failing dispatch tests**

```python
def test_dispatch_revalidates_only_currently_runnable_root() -> None:
    repo, mission_id = invalidated_canonical_runtime()

    records = RevalidationService(repo).dispatch(mission_id, "request-1")
    snapshot = repo.get_snapshot(mission_id)

    assert [record.decision_id for record in records] == ["D42"]
    assert snapshot.decisions["D42"].status is DecisionStatus.REVALIDATING
    assert snapshot.decisions["D42"].execution_count == 2
    assert snapshot.decisions["D50"].status is DecisionStatus.STALE
    assert snapshot.decisions["D50"].execution_count == 1
    assert snapshot.decisions["D43"].status is DecisionStatus.VALID
    assert snapshot.decisions["D43"].execution_count == 1


def test_duplicate_dispatch_request_is_idempotent() -> None:
    repo, mission_id = invalidated_canonical_runtime()
    service = RevalidationService(repo)

    first = service.dispatch(mission_id, "request-1")
    second = service.dispatch(mission_id, "request-1")

    assert second == first
    assert repo.get_snapshot(mission_id).decisions["D42"].execution_count == 2
```

- [x] **Step 5: Implement dispatch and verify GREEN**

Dispatch records contain `dispatch_id`, `request_id`, `decision_id`, `work_type`, and `status="DISPATCHED"`. The service stores the result keyed by request ID so duplicates return the original response without increments.

```bash
cd backend && uv run --group dev pytest tests/test_revalidation.py -v
cd backend && uv run --group dev pytest -v
```

- [x] **Step 6: Commit Task 3**

```bash
git add backend/app/domain/revalidation.py backend/tests/test_revalidation.py
git commit -m "feat: plan selective revalidation"
```

---

### Task 4: FastAPI Gate Contract

**Files:**
- Create: `backend/app/main.py`
- Test: `backend/tests/test_api.py`

**Interfaces:**
- Consumes: repository, fixture, invalidation, and revalidation services.
- Produces: `create_app(repository: GraphRepository | None = None) -> FastAPI`.
- Produces: four endpoints defined by the approved spec.

- [x] **Step 1: Write failing API reset and upgrade tests**

```python
def test_reset_then_upgrade_returns_required_graph_without_direct_status_writes() -> None:
    repo = InMemoryGraphRepository()
    client = TestClient(create_app(repo))

    reset = client.post("/api/demo/reset")
    mission_id = reset.json()["mission_id"]
    drift = client.post(
        "/api/demo/policy/upgrade",
        json={"mission_id": mission_id, "event_id": "evt-api-1"},
    )

    assert drift.status_code == 200
    body = drift.json()
    assert body["summary"] == {"stale": 2, "preserved": 1, "blocked": 1}
    statuses = {node["id"]: node["status"] for node in body["nodes"]}
    assert {node_id: statuses[node_id] for node_id in (
        "D42", "D43", "D50", "activate-vendor"
    )} == {
        "D42": "STALE",
        "D43": "VALID",
        "D50": "STALE",
        "activate-vendor": "BLOCKED",
    }
```

Use a repository test spy that rejects `save_snapshot` when called directly from the route module; only domain services receive write authority. The assertion concerns the boundary, not FastAPI internals.

- [x] **Step 2: Run API test and verify RED**

```bash
cd backend && uv run --group dev pytest tests/test_api.py -v
```

Expected: import failure for `create_app`.

- [x] **Step 3: Implement app factory and graph read model**

Endpoint contracts:

```text
POST /api/demo/reset
POST /api/demo/policy/upgrade
GET  /api/missions/{mission_id}/graph
POST /api/missions/{mission_id}/revalidate
```

The read model returns:

```json
{
  "mission_id": "demo-001",
  "phase": "INITIAL|DRIFTED|REVALIDATING",
  "summary": {"stale": 2, "preserved": 1, "blocked": 1},
  "nodes": [],
  "edges": [],
  "plan": {},
  "events": [],
  "dispatches": []
}
```

Add CORS only for local Vite origins `http://localhost:5173` and `http://127.0.0.1:5173`.

- [x] **Step 4: Add failing duplicate, revalidation, and error contract tests**

Cover duplicate event responses, duplicate request responses, unknown mission 404, mismatched policy version 409, and revalidation before drift 409. Assert status codes and stable machine-readable `detail.code` values.

- [x] **Step 5: Implement minimal errors and verify GREEN**

```bash
cd backend && uv run --group dev pytest tests/test_api.py -v
cd backend && uv run --group dev pytest --cov=app --cov-report=term-missing -v
```

Expected: all backend tests pass; domain service branch coverage is at least 90%.

- [x] **Step 6: Commit Task 4**

```bash
git add backend/app/main.py backend/tests/test_api.py
git commit -m "feat: expose falsification gate API"
```

---

### Task 5: React Flow Read Model and Gate UI

**Files:**
- Create: `frontend/package.json`
- Create: `frontend/tsconfig.json`
- Create: `frontend/vite.config.ts`
- Create: `frontend/index.html`
- Create: `frontend/src/main.tsx`
- Create: `frontend/src/types.ts`
- Create: `frontend/src/api.ts`
- Create: `frontend/src/graph-model.ts`
- Create: `frontend/src/graph-model.test.ts`
- Create: `frontend/src/App.tsx`
- Create: `frontend/src/App.test.tsx`
- Create: `frontend/src/components/DecisionGraph.tsx`
- Create: `frontend/src/components/ProvenancePanel.tsx`
- Create: `frontend/src/components/EventLog.tsx`
- Create: `frontend/src/styles.css`
- Create: `frontend/src/test/setup.ts`

**Interfaces:**
- Consumes: `GET /graph`, `POST /reset`, `POST /policy/upgrade`, `POST /revalidate`.
- Produces: `toFlowElements(readModel: GraphReadModel): { nodes: Node[]; edges: Edge[] }`.
- Produces: `<App api={ContinuumApi}>` with injectable API boundary for real component tests.

- [x] **Step 1: Create frontend test configuration**

Use npm to create a lockfile and install runtime/dev dependencies:

```bash
cd frontend
npm init -y
npm install react react-dom @xyflow/react @dagrejs/dagre lucide-react
npm install -D typescript vite @vitejs/plugin-react vitest jsdom @testing-library/react @testing-library/jest-dom @testing-library/user-event @types/react @types/react-dom
```

Set scripts to `dev`, `build`, `test`, and `test:run`. Configure Vitest `environment: "jsdom"`, `setupFiles: ["./src/test/setup.ts"]`, and Vite proxy `/api -> http://127.0.0.1:8000`.

- [x] **Step 2: Write failing pure graph transformation tests**

```typescript
it('maps drifted statuses and causal edges without ID-specific styling', () => {
  const result = toFlowElements(driftedReadModel);

  expect(result.nodes.map(({ id, type, data }) => ({ id, type, status: data.status }))).toEqual([
    { id: 'policy-v12', type: 'artifact', status: 'SUPERSEDED' },
    { id: 'policy-v13', type: 'artifact', status: 'CURRENT' },
    { id: 'soc2-A31', type: 'evidence', status: 'VALID' },
    { id: 'financial-F7', type: 'evidence', status: 'VALID' },
    { id: 'D42', type: 'decision', status: 'STALE' },
    { id: 'D43', type: 'decision', status: 'VALID' },
    { id: 'D50', type: 'decision', status: 'STALE' },
    { id: 'activate-vendor', type: 'action', status: 'BLOCKED' },
  ]);
  expect(result.edges).toHaveLength(7);
});
```

Production mutation caught: status derived from IDs, dropped supersession edge, or wrong node type mapping.

- [x] **Step 3: Run and verify RED, then implement graph DTOs/transformation**

```bash
cd frontend && npm run test:run -- src/graph-model.test.ts
```

Expected RED: `toFlowElements` missing. Implement strict DTO unions and a relation-driven transformation. Use Dagre with edge direction and node dimensions for layout; never use canonical node IDs to choose positions or styles.

- [x] **Step 4: Write failing App behavior tests with a complete fake API**

```typescript
it('shows drift impact, preserved work, and dispatches only D42', async () => {
  const api = createFakeApi({ initial, drifted, revalidating });
  render(<App api={api} />);

  await userEvent.click(await screen.findByRole('button', { name: 'Inject policy v13' }));
  expect(await screen.findByText('External policy changed.')).toBeVisible();
  expect(screen.getByText('2 stale')).toBeVisible();
  expect(screen.getByText('1 preserved')).toBeVisible();
  expect(screen.getByText('D43', { exact: false })).toBeVisible();

  await userEvent.click(screen.getByRole('button', { name: 'Run affected branch' }));
  expect(api.revalidate).toHaveBeenCalledWith(expect.any(String), expect.any(String));
  expect(await screen.findByText('REVALIDATING')).toBeVisible();
  expect(screen.getByText('Waiting: D50')).toBeVisible();
});
```

The fake mirrors the complete `GraphReadModel`; assertions target rendered behavior. Network transport is the only substituted boundary.

- [x] **Step 5: Run App test and verify RED**

```bash
cd frontend && npm run test:run -- src/App.test.tsx
```

Expected: import failure or missing button/content.

- [x] **Step 6: Implement UI matching the approved benchmark**

Implement:

- one shared light graph surface and right provenance/plan rail;
- custom artifact/evidence/decision/action nodes with text/icon/shape status redundancy;
- summary `2 stale · 1 preserved · 1 blocked` from API counts;
- `Run affected branch` accessible button showing `Run now: D42` detail;
- exact status transitions `INITIAL → DRIFTED → REVALIDATING`;
- one impact-sweep animation based on affected edges, disabled by `prefers-reduced-motion`;
- error state that preserves the current graph and names the failed action;
- 8px spacing tokens, 4px radius, no shadows/gradients/dark mode/card wall;
- tablet layout that stacks the provenance rail below the graph.

- [x] **Step 7: Verify unit tests and production build**

```bash
cd frontend && npm run test:run
cd frontend && npm run build
```

Expected: all tests pass; TypeScript/Vite build exits 0 without warnings.

- [x] **Step 8: Commit Task 5**

```bash
git add frontend
git commit -m "feat: visualize policy drift graph"
```

---

### Task 6: Local Commands, Browser Gate, Documentation, and Report

**Files:**
- Create: `scripts/dev.sh`
- Create: `Makefile`
- Create: `frontend/e2e/gate.spec.ts`
- Modify: `frontend/package.json`
- Modify: `README.md`
- Create: `docs/reports/36h-gate-report.md`

**Interfaces:**
- Produces: `make setup`, `make test`, `make dev`.
- Produces: browser evidence for reset → drift → revalidation.
- Produces: gate report separating automated PASS evidence from the still-human 5-person visual observation.

- [ ] **Step 1: Write the failing Playwright browser contract**

Install Playwright test support and its Chromium browser:

```bash
cd frontend && npm install -D @playwright/test && npx playwright install chromium
```

Create `frontend/e2e/gate.spec.ts`:

```typescript
test('policy drift preserves D43 and dispatches only D42', async ({ page }) => {
  await page.goto('/');
  await expect(page.getByText('All decisions are valid.')).toBeVisible();

  await page.getByRole('button', { name: 'Inject policy v13' }).click();
  await expect(page.getByText('External policy changed.')).toBeVisible();
  await expect(page.getByTestId('node-D42')).toContainText('STALE');
  await expect(page.getByTestId('node-D50')).toContainText('STALE');
  await expect(page.getByTestId('node-D43')).toContainText('VALID');
  await expect(page.getByTestId('node-D43')).toContainText('PRESERVED');
  await expect(page.getByTestId('node-activate-vendor')).toContainText('BLOCKED');

  await page.getByRole('button', { name: 'Run affected branch' }).click();
  await expect(page.getByTestId('node-D42')).toContainText('REVALIDATING');
  await expect(page.getByTestId('node-D43')).toContainText('VALID');
  await expect(page.getByText('Waiting: D50')).toBeVisible();
});
```

Production mutations caught: UI detached from the real API, wrong post-drift statuses, or accidental sibling rerun.

- [ ] **Step 2: Run E2E and verify RED**

Start backend and frontend, then run:

```bash
cd frontend && npx playwright test e2e/gate.spec.ts
```

Expected: test fails until the webServer/start commands and any missing selectors are implemented.

- [ ] **Step 3: Implement repeatable local commands**

`scripts/dev.sh` starts `uv run uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000` and `npm --prefix frontend run dev -- --host 127.0.0.1`, records both PIDs, and traps `EXIT INT TERM` to terminate them.

`Makefile` targets:

```make
setup:
	cd backend && uv sync --group dev
	cd frontend && npm ci

test:
	cd backend && uv run --group dev pytest --cov=app --cov-report=term-missing
	cd frontend && npm run test:run
	cd frontend && npm run build

dev:
	./scripts/dev.sh
```

- [ ] **Step 4: Configure Playwright web servers and verify GREEN**

Configure Playwright to start backend on 8000 and Vite on 4173, use `baseURL: "http://127.0.0.1:4173"`, and retain trace/screenshot on failure.

Run:

```bash
cd frontend && npx playwright test e2e/gate.spec.ts
```

Expected: 1 passed in Chromium.

- [ ] **Step 5: Update README with exact gate commands**

Document prerequisites, `make setup`, `make test`, `make dev`, the four endpoints, the exact expected state, and the explicit exclusions. Keep the repository’s design-pack links.

- [ ] **Step 6: Run the complete automated gate**

```bash
make test
cd frontend && npx playwright test
git diff --check
git status -sb
```

Expected: backend tests, frontend tests, build, and browser test all pass; no whitespace errors; only intended report/doc changes remain.

- [ ] **Step 7: Write the gate report from observed evidence**

Create `docs/reports/36h-gate-report.md` with:

- commit and environment identifiers;
- exact commands and pass/fail counts;
- canonical and alternate fixture outcomes;
- screenshot path from the verified browser state;
- explicit statement that Gemini/ADK/cloud hypotheses were not tested;
- human 5-person visual gate marked `PENDING` until actual participants are observed;
- GO/NO-GO limited to automated kernel/UI readiness, not full-project GO.

Do not claim the complete 36-hour gate passes while the human observation remains pending.

- [ ] **Step 8: Commit Task 6**

```bash
git add Makefile scripts frontend README.md docs/reports/36h-gate-report.md
git commit -m "test: verify falsification gate flow"
```

---

## Completion Audit

Before declaring implementation complete, inspect current evidence for every item:

1. Required four-state outcome: backend exact fixture test and real API/browser state.
2. No ID hardcoding: alternate fixture test plus source review for canonical IDs outside fixture/tests/UI example data.
3. Determinism: duplicate, cycle, edge-criticality, and version-mismatch tests.
4. Selective rerun: planner test, execution counts, API response, and browser state.
5. Simulator safety: route boundary test and source inspection showing no direct Decision/Action status assignment in `main.py`.
6. Visual clarity implementation: benchmark comparison, status redundancy, reduced motion, responsive layout, screenshot.
7. Human 15-second gate: five recorded observations; absence means the gate is not fully passed.
8. Scope: dependency manifests and source tree contain no Gemini, ADK, Firestore, Pub/Sub, commitments, side-effect execution, or cloud deployment code.
9. Reproducibility: fresh `make setup`, `make test`, and `make dev` behavior.
10. Repository state: clean worktree, pushed implementation branch, and review/integration decision handled via `superpowers:finishing-a-development-branch`.
