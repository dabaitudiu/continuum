# Local Semantic Runtime Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build Continuum's durable deterministic runtime kernel with Mission/Work state machines, commitments, side-effect safety, audit/outbox transactions, SQLite restart recovery, and compatible Phase G APIs.

**Architecture:** Pure domain services produce explicit `RuntimeMutation` values; a `RuntimeCoordinator` is the only application-layer writer. In-memory and SQLite repositories implement the same optimistic-concurrency contract, with state, inbox, audit, and outbox committed atomically. Existing graph invalidation remains the canonical graph engine and is migrated behind a compatibility adapter only after the new runtime path is proven.

**Tech Stack:** Python 3.11+, Pydantic 2, FastAPI, standard-library `sqlite3`, pytest, pytest-cov

**Spec:** `docs/superpowers/specs/2026-08-18-local-semantic-runtime-design.md`

## Global Constraints

- The runtime, never Gemini or an agent, owns canonical invalidation and state transitions.
- Preserve the existing Policy v12 → v13, D42/D50 stale, D43 valid, selective D42 revalidation behavior.
- Every mutation is idempotent by stable request/event id and commits state, inbox result, audit, and outbox atomically.
- Only `VALID` decisions authorize side effects; unknown execution outcomes require reconciliation before retry.
- SQLite is the local default and must recover a complete mission through a new repository instance.
- Do not modify or stage the user's unrelated `AGENTS.md` change.
- Do not add Gemini, ADK, Firestore, Pub/Sub, UI, or cloud placeholders in this milestone.

## File Map

- `backend/app/runtime/entities.py`: Mission, WorkItem, Commitment, SideEffect, Audit, inbox/outbox and aggregate models.
- `backend/app/runtime/errors.py`: stable typed domain errors.
- `backend/app/runtime/state_machine.py`: pure Mission and WorkItem transition validation.
- `backend/app/runtime/commitments.py`: pure event-to-commitment matching and satisfaction.
- `backend/app/runtime/side_effects.py`: pure side-effect ledger transition rules.
- `backend/app/runtime/mutations.py`: explicit repository mutation model.
- `backend/app/runtime/coordinator.py`: command/event orchestration and cross-entity invariants.
- `backend/app/repository/runtime_protocol.py`: repository contract.
- `backend/app/repository/runtime_memory.py`: in-memory contract implementation.
- `backend/app/repository/runtime_sqlite.py`: normalized SQLite implementation and schema.
- `backend/app/demo/runtime_fixture.py`: durable vendor-onboarding mission seed.
- `backend/app/api/runtime_routes.py`: runtime REST routes and error mapping.
- `backend/app/main.py`: application composition and Phase G compatibility wiring.

---

### Task 1: Runtime Entities and State Machines

**Files:**
- Create: `backend/app/runtime/__init__.py`
- Create: `backend/app/runtime/entities.py`
- Create: `backend/app/runtime/errors.py`
- Create: `backend/app/runtime/state_machine.py`
- Test: `backend/tests/runtime/test_state_machine.py`

**Interfaces:**
- Produces: `Mission`, `WorkItem`, `MissionStatus`, `WorkStatus`, `RuntimeSnapshot`, `RuntimeError`, `MissionStateMachine.transition()`, `WorkStateMachine.transition()`.
- Consumes: existing `GraphSnapshot` from `app.domain.models`.

- [ ] **Step 1: Write failing transition-table tests**

```python
@pytest.mark.parametrize(
    ("current", "target"),
    [
        (MissionStatus.CREATED, MissionStatus.RUNNING),
        (MissionStatus.RUNNING, MissionStatus.WAITING),
        (MissionStatus.RUNNING, MissionStatus.REVALIDATING),
        (MissionStatus.WAITING, MissionStatus.RUNNING),
        (MissionStatus.REVALIDATING, MissionStatus.WAITING),
        (MissionStatus.REVALIDATING, MissionStatus.RUNNING),
        (MissionStatus.BLOCKED, MissionStatus.RUNNING),
        (MissionStatus.RUNNING, MissionStatus.COMPLETED),
    ],
)
def test_allowed_mission_transitions(current, target):
    mission = Mission(mission_id="m-1", status=current)
    assert MissionStateMachine.transition(mission, target).status is target

def test_terminal_mission_cannot_restart():
    with pytest.raises(RuntimeError, match="INVALID_MISSION_TRANSITION"):
        MissionStateMachine.transition(
            Mission(mission_id="m-1", status=MissionStatus.COMPLETED),
            MissionStatus.RUNNING,
        )

def test_waiting_work_requires_open_commitment():
    work = WorkItem(work_item_id="w-1", mission_id="m-1", work_type="SECURITY_REVIEW")
    with pytest.raises(RuntimeError, match="COMMITMENT_INVARIANT_VIOLATION"):
        WorkStateMachine.transition(work, WorkStatus.WAITING, has_open_commitment=False)
```

- [ ] **Step 2: Run the focused tests and verify RED**

Run: `uv run --project backend pytest backend/tests/runtime/test_state_machine.py -v`

Expected: collection fails because `app.runtime` does not exist.

- [ ] **Step 3: Implement focused Pydantic entities and typed errors**

```python
class RuntimeError(Exception):
    def __init__(self, code: str, message: str) -> None:
        self.code = code
        self.message = message
        super().__init__(f"{code}: {message}")

class MissionStatus(StrEnum):
    CREATED = "CREATED"
    RUNNING = "RUNNING"
    WAITING = "WAITING"
    REVALIDATING = "REVALIDATING"
    BLOCKED = "BLOCKED"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"

class Mission(BaseModel):
    mission_id: str
    status: MissionStatus = MissionStatus.CREATED
    revision: int = Field(default=0, ge=0)
    event_sequence: int = Field(default=0, ge=0)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
```

Define `WorkStatus`, `CommitmentStatus`, `SideEffectStatus`, `WorkItem`, `Commitment`, `SideEffectRecord`, `AuditEvent`, `InboxRecord`, `OutboxMessage`, and `RuntimeSnapshot` in the same file. Use default factories for mutable collections and timezone-aware UTC timestamps.

- [ ] **Step 4: Implement explicit transition maps**

```python
MISSION_TRANSITIONS = {
    MissionStatus.CREATED: {MissionStatus.RUNNING, MissionStatus.CANCELLED},
    MissionStatus.RUNNING: {
        MissionStatus.WAITING, MissionStatus.REVALIDATING, MissionStatus.BLOCKED,
        MissionStatus.COMPLETED, MissionStatus.FAILED, MissionStatus.CANCELLED,
    },
    MissionStatus.WAITING: {
        MissionStatus.RUNNING, MissionStatus.REVALIDATING,
        MissionStatus.BLOCKED, MissionStatus.FAILED, MissionStatus.CANCELLED,
    },
    MissionStatus.REVALIDATING: {
        MissionStatus.RUNNING, MissionStatus.WAITING, MissionStatus.BLOCKED,
        MissionStatus.FAILED, MissionStatus.CANCELLED,
    },
    MissionStatus.BLOCKED: {
        MissionStatus.RUNNING, MissionStatus.REVALIDATING,
        MissionStatus.FAILED, MissionStatus.CANCELLED,
    },
    MissionStatus.COMPLETED: set(),
    MissionStatus.FAILED: set(),
    MissionStatus.CANCELLED: set(),
}
```

Return deep copies with updated status; reject missing commitment on WorkItem `WAITING`; increment `attempt` only on `PENDING → DISPATCHED`.

- [ ] **Step 5: Run tests and commit**

Run: `uv run --project backend pytest backend/tests/runtime/test_state_machine.py -v`

Expected: PASS.

```bash
git add backend/app/runtime backend/tests/runtime/test_state_machine.py
git commit -m "feat: define runtime state machines"
```

### Task 2: Commitment Matching and Superseding Decisions

**Files:**
- Create: `backend/app/runtime/commitments.py`
- Create: `backend/app/runtime/decisions.py`
- Modify: `backend/app/domain/models.py`
- Test: `backend/tests/runtime/test_commitments.py`
- Test: `backend/tests/runtime/test_decisions.py`

**Interfaces:**
- Consumes: `Commitment`, `CommitmentStatus`, `DomainEvent`, `GraphSnapshot`.
- Produces: `CommitmentService.match()`, `CommitmentService.satisfy()`, `DecisionService.supersede()`.

- [ ] **Step 1: Write failing commitment and decision-history tests**

```python
def test_only_matching_document_event_satisfies_commitment():
    commitment = open_pen_test_commitment()
    wrong = DomainEvent(event_id="e-1", event_type="vendor.document.uploaded", payload={
        "vendor_id": "ACME", "document_type": "SOC2", "document_id": "doc-1"
    })
    right = DomainEvent(event_id="e-2", event_type="vendor.document.uploaded", payload={
        "vendor_id": "ACME", "document_type": "PEN_TEST", "document_id": "doc-2"
    })
    assert not CommitmentService.match(commitment, wrong)
    assert CommitmentService.satisfy(commitment, right).status is CommitmentStatus.SATISFIED

def test_supersede_preserves_old_decision_and_creates_new_one():
    result = DecisionService.supersede(graph_with_stale_d42(), old_id="D42", new_id="D57", outcome="APPROVED")
    assert result.decisions["D42"].status is DecisionStatus.SUPERSEDED
    assert result.decisions["D57"].status is DecisionStatus.VALID
    assert result.decisions["D57"].supersedes_decision_id == "D42"
```

- [ ] **Step 2: Run focused tests and verify RED**

Run: `uv run --project backend pytest backend/tests/runtime/test_commitments.py backend/tests/runtime/test_decisions.py -v`

Expected: imports fail or enum members are missing.

- [ ] **Step 3: Implement predicate matching and one-way satisfaction**

```python
@staticmethod
def match(commitment: Commitment, event: DomainEvent) -> bool:
    return (
        commitment.status is CommitmentStatus.OPEN
        and commitment.event_type == event.event_type
        and all(event.payload.get(key) == value for key, value in commitment.predicate.items())
    )
```

`satisfy()` raises `INVALID_COMMITMENT_TRANSITION` unless status is `OPEN`, and records `satisfied_by_event_id` plus `satisfied_at`.

- [ ] **Step 4: Extend decision lifecycle and implement immutable supersession**

Add `INVALID` and `SUPERSEDED` to `DecisionStatus`. `DecisionService.supersede()` must require old status `STALE` or `REVALIDATING`, create a new `VALID` node, mark the old node `SUPERSEDED`, and redirect outgoing dependency edges from old id to new id while retaining provenance edges and old node history.

- [ ] **Step 5: Run focused and Phase G regression tests, then commit**

Run: `uv run --project backend pytest backend/tests/runtime/test_commitments.py backend/tests/runtime/test_decisions.py backend/tests/test_invalidation.py backend/tests/test_revalidation.py -v`

Expected: PASS.

```bash
git add backend/app/runtime backend/app/domain/models.py backend/tests/runtime
git commit -m "feat: model commitments and decision supersession"
```

### Task 3: Side Effect Ledger Safety

**Files:**
- Create: `backend/app/runtime/side_effects.py`
- Test: `backend/tests/runtime/test_side_effects.py`

**Interfaces:**
- Consumes: `SideEffectRecord`, `SideEffectStatus`, `DecisionStatus`.
- Produces: `SideEffectLedger.intent()`, `begin()`, `commit()`, `record_unknown()`, `reconcile()`.

- [ ] **Step 1: Write failing authorization, idempotency, and reconciliation tests**

```python
def test_stale_decision_cannot_authorize_side_effect():
    with pytest.raises(RuntimeError, match="STALE_AUTHORIZATION"):
        SideEffectLedger.begin(intended_effect(), DecisionStatus.STALE)

def test_committed_effect_is_idempotent():
    effect = committed_effect(idempotency_key="activate:ACME")
    assert SideEffectLedger.begin(effect, DecisionStatus.VALID) == effect

def test_unknown_result_requires_reconciliation_before_retry():
    unknown = SideEffectLedger.record_unknown(executing_effect())
    assert unknown.status is SideEffectStatus.RECONCILIATION_REQUIRED
    with pytest.raises(RuntimeError, match="SIDE_EFFECT_RECONCILIATION_REQUIRED"):
        SideEffectLedger.begin(unknown, DecisionStatus.VALID)
```

- [ ] **Step 2: Run focused tests and verify RED**

Run: `uv run --project backend pytest backend/tests/runtime/test_side_effects.py -v`

Expected: `SideEffectLedger` import fails.

- [ ] **Step 3: Implement explicit ledger transitions**

```python
@staticmethod
def begin(effect: SideEffectRecord, authorization: DecisionStatus) -> SideEffectRecord:
    if effect.status is SideEffectStatus.COMMITTED:
        return effect.model_copy(deep=True)
    if authorization is not DecisionStatus.VALID:
        raise RuntimeError("STALE_AUTHORIZATION", "only a VALID decision may authorize a side effect")
    if effect.status is SideEffectStatus.RECONCILIATION_REQUIRED:
        raise RuntimeError("SIDE_EFFECT_RECONCILIATION_REQUIRED", "reconcile before retry")
    if effect.status is not SideEffectStatus.INTENDED:
        raise RuntimeError("INVALID_SIDE_EFFECT_TRANSITION", f"cannot begin from {effect.status}")
    return effect.model_copy(update={"status": SideEffectStatus.EXECUTING}, deep=True)
```

Implement the remaining transitions with no direct `EXECUTING → INTENDED` path. `reconcile(externally_committed=True)` returns `COMMITTED`; false returns `FAILED_RETRYABLE`.

- [ ] **Step 4: Run tests and commit**

Run: `uv run --project backend pytest backend/tests/runtime/test_side_effects.py -v`

Expected: PASS.

```bash
git add backend/app/runtime/side_effects.py backend/tests/runtime/test_side_effects.py
git commit -m "feat: enforce side effect ledger safety"
```

### Task 4: Runtime Repository Contract and In-Memory Implementation

**Files:**
- Create: `backend/app/runtime/mutations.py`
- Create: `backend/app/repository/runtime_protocol.py`
- Create: `backend/app/repository/runtime_memory.py`
- Test: `backend/tests/repository/runtime_contract.py`
- Test: `backend/tests/repository/test_runtime_memory.py`

**Interfaces:**
- Consumes: `RuntimeSnapshot`, runtime entities.
- Produces: `RuntimeMutation`, `RuntimeRepository.load()`, `commit()`, `find_inbox()`, `InMemoryRuntimeRepository.create()`.

- [ ] **Step 1: Write a reusable repository contract suite**

```python
def assert_runtime_repository_contract(repo):
    repo.create(runtime_snapshot("m-1"))
    initial = repo.load("m-1")
    committed = repo.commit("m-1", initial.mission.revision, mutation_to_running(initial))
    assert committed.mission.status is MissionStatus.RUNNING
    assert committed.mission.revision == 1
    assert committed.mission.event_sequence == 1
    assert repo.find_inbox("m-1", "request-1").result["status"] == "RUNNING"
    with pytest.raises(RuntimeError, match="REVISION_CONFLICT"):
        repo.commit("m-1", 0, mutation_to_waiting(committed))
```

The contract must also assert deep-copy isolation, duplicate inbox rejection, monotonic audit sequence, and atomic rollback when a mutation contains a duplicate side-effect idempotency key.

- [ ] **Step 2: Run in-memory repository test and verify RED**

Run: `uv run --project backend pytest backend/tests/repository/test_runtime_memory.py -v`

Expected: runtime repository modules do not exist.

- [ ] **Step 3: Define explicit mutation and repository protocol**

```python
class RuntimeMutation(BaseModel):
    mission: Mission
    work_upserts: list[WorkItem] = Field(default_factory=list)
    commitment_upserts: list[Commitment] = Field(default_factory=list)
    side_effect_upserts: list[SideEffectRecord] = Field(default_factory=list)
    graph: GraphSnapshot | None = None
    audit_appends: list[AuditEvent] = Field(default_factory=list)
    inbox_completion: InboxRecord
    outbox_appends: list[OutboxMessage] = Field(default_factory=list)

class RuntimeRepository(Protocol):
    def create(self, snapshot: RuntimeSnapshot) -> None: ...
    def load(self, mission_id: str) -> RuntimeSnapshot: ...
    def find_inbox(self, mission_id: str, message_id: str) -> InboxRecord | None: ...
    def commit(self, mission_id: str, expected_revision: int, mutation: RuntimeMutation) -> RuntimeSnapshot: ...
```

- [ ] **Step 4: Implement in-memory atomic copy-on-commit**

Build the proposed snapshot on a deep copy, validate revision/inbox/idempotency/sequence constraints, then replace the stored snapshot only after every validation succeeds. Protect operations with `threading.RLock` so the concurrency contract is deterministic.

- [ ] **Step 5: Run contract tests and commit**

Run: `uv run --project backend pytest backend/tests/repository/test_runtime_memory.py -v`

Expected: PASS.

```bash
git add backend/app/runtime/mutations.py backend/app/repository backend/tests/repository
git commit -m "feat: add atomic runtime repository contract"
```

### Task 5: SQLite Persistence, Recovery, and Concurrency

**Files:**
- Create: `backend/app/repository/runtime_sqlite.py`
- Test: `backend/tests/repository/test_runtime_sqlite.py`

**Interfaces:**
- Consumes: the Task 4 `RuntimeRepository` contract and `RuntimeMutation`.
- Produces: `SQLiteRuntimeRepository(path: Path)` and `close()`.

- [ ] **Step 1: Run the shared contract against SQLite and add restart/concurrency tests**

```python
def test_sqlite_repository_contract(tmp_path):
    repo = SQLiteRuntimeRepository(tmp_path / "runtime.db")
    assert_runtime_repository_contract(repo)

def test_new_instance_recovers_complete_runtime_snapshot(tmp_path):
    path = tmp_path / "runtime.db"
    first = SQLiteRuntimeRepository(path)
    expected = persisted_waiting_snapshot(first)
    first.close()
    second = SQLiteRuntimeRepository(path)
    assert second.load(expected.mission.mission_id) == expected

def test_two_writers_cannot_overwrite_same_revision(tmp_path):
    repo = SQLiteRuntimeRepository(tmp_path / "runtime.db")
    repo.create(runtime_snapshot("m-1"))
    base = repo.load("m-1")
    repo.commit("m-1", base.mission.revision, mutation_to_running(base, "r-1"))
    with pytest.raises(RuntimeError, match="REVISION_CONFLICT"):
        repo.commit("m-1", base.mission.revision, mutation_to_running(base, "r-2"))
```

- [ ] **Step 2: Run SQLite tests and verify RED**

Run: `uv run --project backend pytest backend/tests/repository/test_runtime_sqlite.py -v`

Expected: `SQLiteRuntimeRepository` import fails.

- [ ] **Step 3: Implement schema and serialization helpers**

Use `sqlite3.connect(path, isolation_level=None, check_same_thread=False)`, `PRAGMA foreign_keys = ON`, and `BEGIN IMMEDIATE` for mutations. Create normalized tables named in the spec with primary/unique keys for revision, inbox message, audit sequence, and side-effect idempotency. Store Pydantic payloads with `model_dump_json()` and recover with `model_validate_json()`.

- [ ] **Step 4: Implement transactional create/load/commit**

Within one `BEGIN IMMEDIATE` transaction: compare revision, validate the full mutation, upsert entity rows, replace graph child rows for the mission, append inbox/audit/outbox, update Mission revision, and `COMMIT`. On any exception call `ROLLBACK` and re-raise the stable `RuntimeError`.

- [ ] **Step 5: Run contract, restart, concurrency, and branch coverage tests**

Run: `uv run --project backend pytest backend/tests/repository -v --cov=app.repository.runtime_sqlite --cov-branch --cov-report=term-missing`

Expected: PASS with no uncovered branch representing a transaction outcome.

- [ ] **Step 6: Commit**

```bash
git add backend/app/repository/runtime_sqlite.py backend/tests/repository/test_runtime_sqlite.py
git commit -m "feat: persist runtime state in sqlite"
```

### Task 6: Runtime Coordinator and Vendor-Onboarding Event Flow

**Files:**
- Create: `backend/app/runtime/coordinator.py`
- Create: `backend/app/demo/runtime_fixture.py`
- Test: `backend/tests/runtime/test_coordinator.py`

**Interfaces:**
- Consumes: `RuntimeRepository`, state services, `DomainEvent`.
- Produces: `RuntimeCoordinator.create_demo()`, `start()`, `process_event()`, `get()`, `timeline()`, `commitments()`.

- [ ] **Step 1: Write failing end-to-end domain tests**

```python
def test_start_is_idempotent_and_creates_waiting_pen_test_commitment():
    coordinator = coordinator_with_memory_repo()
    created = coordinator.create_demo("create-1")
    first = coordinator.start(created.mission.mission_id, "start-1")
    second = coordinator.start(created.mission.mission_id, "start-1")
    assert first.snapshot.mission.status is MissionStatus.WAITING
    assert second.duplicate is True
    assert len(first.snapshot.commitments) == 1
    assert first.snapshot.commitments[0].predicate == {
        "vendor_id": "ACME", "document_type": "PEN_TEST"
    }

def test_wrong_event_does_not_wake_but_right_event_wakes_exactly_once():
    coordinator, mission_id = waiting_demo()
    wrong = coordinator.process_event(document_event("evt-1", "SOC2"))
    right = coordinator.process_event(document_event("evt-2", "PEN_TEST"))
    duplicate = coordinator.process_event(document_event("evt-2", "PEN_TEST"))
    assert wrong.snapshot.mission.status is MissionStatus.WAITING
    assert right.snapshot.mission.status is MissionStatus.RUNNING
    assert len([w for w in right.snapshot.work_items if w.work_type == "REVIEW_PEN_TEST"]) == 1
    assert duplicate.duplicate is True
```

Also assert audit sequences are contiguous, every mutation writes an outbox message, and an injected repository failure leaves the pre-command snapshot unchanged.

- [ ] **Step 2: Run coordinator tests and verify RED**

Run: `uv run --project backend pytest backend/tests/runtime/test_coordinator.py -v`

Expected: coordinator and runtime fixture imports fail.

- [ ] **Step 3: Implement the canonical demo seed**

Create a `CREATED` ACME Mission containing the existing canonical Phase G `GraphSnapshot`, one initial intake WorkItem, no commitments, and no side effects. Derive the mission namespace with UUIDv5 from the create `request_id`, so replaying the same create request resolves to the same Mission; use deterministic IDs within that Mission. Persist the creation inbox result, first audit event, and outbox event with the initial snapshot.

- [ ] **Step 4: Implement command helper and atomic start/event flows**

```python
def _duplicate_or_snapshot(self, mission_id: str, message_id: str) -> CommandResult | None:
    existing = self._repo.find_inbox(mission_id, message_id)
    if existing is None:
        return None
    return CommandResult(snapshot=self._repo.load(mission_id), duplicate=True, result=existing.result)
```

`start()` transitions CREATED → RUNNING, completes intake deterministically, creates a waiting security WorkItem plus open pen-test Commitment, then derives Mission `WAITING` in one mutation. `process_event()` records unmatched valid events without waking; matched events satisfy the Commitment, create one `REVIEW_PEN_TEST` WorkItem, and transition to `RUNNING` in one mutation.

- [ ] **Step 5: Run coordinator, repository, and Phase G tests**

Run: `uv run --project backend pytest backend/tests/runtime backend/tests/repository backend/tests/test_invalidation.py backend/tests/test_revalidation.py -v`

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add backend/app/runtime/coordinator.py backend/app/demo/runtime_fixture.py backend/tests/runtime/test_coordinator.py
git commit -m "feat: coordinate durable mission events"
```

### Task 7: Runtime REST API and Stable Errors

**Files:**
- Create: `backend/app/api/__init__.py`
- Create: `backend/app/api/runtime_routes.py`
- Modify: `backend/app/main.py`
- Modify: `.gitignore`
- Test: `backend/tests/test_runtime_api.py`

**Interfaces:**
- Consumes: `RuntimeCoordinator` and `RuntimeRepository`.
- Produces: `/api/missions/demo`, `/start`, mission summary, timeline, commitments, and `/api/events`.

- [ ] **Step 1: Write failing API contract tests**

```python
def test_runtime_api_create_start_read_and_wake(tmp_path):
    client = TestClient(create_app(runtime_repository=SQLiteRuntimeRepository(tmp_path / "api.db")))
    created = client.post("/api/missions/demo", json={"request_id": "create-1"})
    mission_id = created.json()["mission_id"]
    waiting = client.post(f"/api/missions/{mission_id}/start", json={"request_id": "start-1"})
    assert waiting.json()["status"] == "WAITING"
    assert client.get(f"/api/missions/{mission_id}/commitments").json()[0]["status"] == "OPEN"
    woke = client.post("/api/events", json=pen_test_event_payload(mission_id, "evt-pen-1"))
    assert woke.json()["status"] == "RUNNING"
    sequences = [event["event_sequence"] for event in client.get(
        f"/api/missions/{mission_id}/timeline"
    ).json()]
    assert sequences == list(range(1, len(sequences) + 1))

def test_duplicate_start_returns_success_with_duplicate_flag(client):
    first = client.post("/api/missions/m-1/start", json={"request_id": "start-1"})
    second = client.post("/api/missions/m-1/start", json={"request_id": "start-1"})
    assert second.status_code == 200
    assert second.json()["duplicate"] is True
```

Add tests for 404 `MISSION_NOT_FOUND`, 409 `INVALID_MISSION_TRANSITION`/`REVISION_CONFLICT`, and 422 `EVENT_SCHEMA_INVALID`.

- [ ] **Step 2: Run API tests and verify RED**

Run: `uv run --project backend pytest backend/tests/test_runtime_api.py -v`

Expected: new routes return 404.

- [ ] **Step 3: Implement request schemas, router, and error handler**

```python
@router.post("/api/events")
def process_event(request: EventEnvelopeRequest) -> dict[str, Any]:
    return to_command_response(coordinator.process_event(request.to_domain_event()))

@app.exception_handler(RuntimeError)
def runtime_error_handler(_request: Request, error: RuntimeError) -> JSONResponse:
    status = 404 if error.code == "MISSION_NOT_FOUND" else 422 if error.code == "EVENT_SCHEMA_INVALID" else 409
    return JSONResponse(status_code=status, content={"detail": {"code": error.code, "message": error.message}})
```

Keep composition injectable for tests. Production app uses `CONTINUUM_DB_PATH` if set, otherwise `backend/data/continuum.db`; create only the containing `backend/data` directory, never a broad path. Add `backend/data/*.db*` to `.gitignore` so local runtime state is never committed.

- [ ] **Step 4: Run API and full backend tests**

Run: `uv run --project backend pytest backend/tests -v`

Expected: all new and existing tests PASS.

- [ ] **Step 5: Commit**

```bash
git add .gitignore backend/app/api backend/app/main.py backend/tests/test_runtime_api.py
git commit -m "feat: expose durable runtime api"
```

### Task 8: Phase G Compatibility Migration and Milestone Verification

**Files:**
- Create: `backend/app/repository/graph_adapter.py`
- Modify: `backend/app/repository/protocol.py`
- Modify: `backend/app/repository/memory.py`
- Modify: `backend/app/domain/invalidation.py`
- Modify: `backend/app/domain/revalidation.py`
- Modify: `backend/app/main.py`
- Modify: `backend/app/demo/fixture.py`
- Modify: `README.md`
- Create: `docs/reports/local-semantic-runtime-report.md`
- Test: `backend/tests/repository/test_graph_adapter.py`
- Test: `backend/tests/test_runtime_restart_api.py`

**Interfaces:**
- Consumes: SQLite runtime repository and all existing Phase G graph service interfaces.
- Produces: `RuntimeGraphRepositoryAdapter` implementing `GraphRepository` over a mission's persisted graph.

- [ ] **Step 1: Write failing adapter and real restart API tests**

```python
def test_phase_g_graph_survives_runtime_repository_restart(tmp_path):
    path = tmp_path / "continuum.db"
    first = TestClient(create_app(runtime_repository=SQLiteRuntimeRepository(path)))
    mission_id = first.post("/api/demo/reset").json()["mission_id"]
    first.post("/api/demo/policy/upgrade", json={"mission_id": mission_id, "event_id": "drift-1"})
    second = TestClient(create_app(runtime_repository=SQLiteRuntimeRepository(path)))
    graph = second.get(f"/api/missions/{mission_id}/graph").json()
    assert graph["summary"] == {"stale": 2, "preserved": 1, "blocked": 1}

def test_phase_g_and_runtime_routes_share_one_mission(tmp_path):
    client = durable_client(tmp_path)
    mission_id = client.post("/api/missions/demo", json={"request_id": "create-1"}).json()["mission_id"]
    assert client.get(f"/api/missions/{mission_id}").status_code == 200
    assert client.get(f"/api/missions/{mission_id}/graph").status_code == 200
```

- [ ] **Step 2: Run compatibility tests and verify RED**

Run: `uv run --project backend pytest backend/tests/repository/test_graph_adapter.py backend/tests/test_runtime_restart_api.py -v`

Expected: adapter import fails or Phase G reset remains in-memory.

- [ ] **Step 3: Implement the compatibility adapter and unified seeding**

Extend `GraphRepository.save_snapshot()` with optional keyword-only `processed_event_id` and `processed_request_id`. Change `InvalidationService` and `RevalidationService` to pass the corresponding id in the same `save_snapshot()` call instead of calling `mark_*_processed()` afterward. Keep the old mark methods only for protocol compatibility tests. Map the adapter's atomic save to one runtime mutation containing graph, inbox, audit, and outbox; no route writes snapshot state directly.

- [ ] **Step 4: Update operator documentation and evidence report**

Document:

```text
make setup
make test
make test-e2e
make dev
```

Explain the default SQLite path, `CONTINUUM_DB_PATH`, reset namespace behavior, current local-only boundary, test counts, branch coverage, restart evidence, and the next milestone (Mission Control UI). Do not claim Gemini/ADK/Google Cloud completion.

- [ ] **Step 5: Run formatting/static sanity and complete verification**

Run:

```bash
git diff --check
uv run --project backend pytest backend/tests --cov=app --cov-branch --cov-report=term-missing
npm --prefix frontend run test:run
npm --prefix frontend run build
cd frontend && env -u NO_COLOR npx playwright test
```

Expected: backend and frontend suites PASS, frontend production build succeeds, Playwright passes, backend branch coverage is at least 98%, and no diff whitespace errors occur.

- [ ] **Step 6: Record exact evidence and commit**

Write the observed commands, test counts, coverage, restart test name, and any honest remaining limitations into `docs/reports/local-semantic-runtime-report.md`.

```bash
git add backend/app/repository backend/app/domain/invalidation.py backend/app/domain/revalidation.py backend/app/main.py backend/app/demo/fixture.py backend/tests README.md docs/reports/local-semantic-runtime-report.md
git commit -m "feat: complete persistent semantic runtime"
```

- [ ] **Step 7: Check repository scope before integration**

Run: `git status --short && git log --oneline --decorate -12`

Expected: only the user's pre-existing `AGENTS.md` edit remains unstaged; all milestone files are committed.
