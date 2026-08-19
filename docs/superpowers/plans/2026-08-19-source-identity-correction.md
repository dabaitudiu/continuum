# Source Identity Correction Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Correct Phase A identity semantics so business revisions, parser representations, arbitrary structured keys, and arrays have deterministic non-retargeting provenance.

**Architecture:** Split immutable business `Revision` from immutable `ParsedRepresentation`, make fragments representation-owned, and qualify canonical refs with representation identity. Bind both layers in `WorldSnapshot`; make arrays atomic unless a stable-key strategy is explicitly configured.

**Tech Stack:** Python 3.11+, Pydantic 2, pytest, standard-library `hashlib`, `json`, and `urllib.parse`.

**Spec:** `docs/superpowers/specs/2026-08-19-source-identity-correction-design.md`

## Global Constraints

- Runtime state machines remain untouched; this is source identity only.
- Registry-generated provenance refs are always representation-qualified.
- Unqualified refs are snapshot-relative shorthand, never persisted canonical provenance.
- Positional array indexes are never emitted as stable fragment identities.
- All new behavior follows test-first red-green-refactor cycles.
- Do not stage the user's unrelated `AGENTS.md` working-tree change.

---

### Task 1: Separate revision and parsed representation identities

**Files:**
- Modify: `backend/app/sources/identity.py`
- Modify: `backend/app/sources/__init__.py`
- Modify: `backend/tests/compiler/test_source_identity.py`

**Interfaces:**
- Produces: `ParsedRepresentation(representation_id, revision_id, parser_version, parser_config_hash, created_at)`.
- Produces: `Fragment.representation_id: str` instead of `Fragment.revision_id`.
- Produces: `IngestedSource(revision, representation, fragments)` from `ingest_json_revision(...)`.
- Produces: `SourceRef(..., representation_id: str | None)` using qualified grammar `artifact@revision!representation#path`.

- [ ] **Step 1: Add failing coexistence and qualified-reference tests**

Add tests proving that identical content under `v12` and `v13` has different `revision_id`, one revision parsed by `json-v1` and `json-v2` has one revision identity but two representation identities, and a qualified ref round-trips all four components.

```python
assert v12.revision.revision_id != v13.revision.revision_id
assert parser_v1.revision.revision_id == parser_v2.revision.revision_id
assert parser_v1.representation.representation_id != parser_v2.representation.representation_id
assert SourceRef.parse(str(ref)) == ref
```

- [ ] **Step 2: Run the focused tests and verify RED**

Run:

```bash
uv run --project backend pytest backend/tests/compiler/test_source_identity.py -q
```

Expected: failures because `ParsedRepresentation`, `IngestedSource.representation`, and qualified `SourceRef` do not exist, and revision identity still depends on parser output.

- [ ] **Step 3: Implement the identity split and canonical encoding**

Implement:

```python
class ParsedRepresentation(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    representation_id: str
    revision_id: str
    parser_version: str
    parser_config_hash: str
    created_at: datetime

class SourceRef(BaseModel):
    artifact_id: str
    revision_label: str
    representation_id: str | None = None
    logical_path: str
```

Derive revision identity from `{artifact_id, revision_label}` and representation identity from `{revision_id, parser_version, parser_config_hash}`. Serialize every ref component with canonical percent encoding and reject non-canonical encodings on parse.

- [ ] **Step 4: Run the focused tests and verify GREEN**

Run the Task 1 command. Expected: all source-identity tests pass.

- [ ] **Step 5: Commit Task 1**

```bash
git add backend/app/sources/identity.py backend/app/sources/__init__.py backend/tests/compiler/test_source_identity.py
git commit -m "fix: separate source and parser identities"
```

### Task 2: Support arbitrary field names and deterministic arrays

**Files:**
- Modify: `backend/app/sources/identity.py`
- Modify: `backend/tests/compiler/test_source_identity.py`

**Interfaces:**
- Consumes: `ParsedRepresentation`, qualified `SourceRef`, and `IngestedSource` from Task 1.
- Produces: `ingest_json_revision(..., array_identity_keys: Mapping[str, str] | None = None)`.
- Produces: atomic array fragments by default and stable selector paths for configured keyed arrays.

- [ ] **Step 1: Add failing arbitrary-key and array tests**

Cover field names containing `@`, `#`, quotes, Unicode, slash, and `%`. Cover default atomic arrays and keyed arrays before/after an insertion:

```python
assert SourceRef.parse(str(special_ref)) == special_ref
assert "$.controls[0].result" not in paths
assert "$.controls" in paths
assert before.fragment_at('$.controls[id="B"].result').logical_path == after.fragment_at('$.controls[id="B"].result').logical_path
```

Add rejection tests for duplicate stable keys, missing keys, non-object items, and non-scalar keys.

- [ ] **Step 2: Run focused tests and verify RED**

Run the Task 1 command. Expected: special keys fail current ref validation and arrays still emit positional paths.

- [ ] **Step 3: Implement field encoding and array strategies**

Keep decoded JSONPath-like logical paths in models. Canonical ref serialization percent-encodes delimiter-bearing characters. Change the JSON traversal so an unconfigured list returns one `(path, list_value)` leaf. For configured paths, validate unique scalar item keys and traverse items using selectors generated from canonical JSON scalar encoding.

Include a sorted `array_identity_keys` mapping in `parser_config_hash`.

- [ ] **Step 4: Run focused tests and verify GREEN**

Run the Task 1 command. Expected: all source-identity tests pass.

- [ ] **Step 5: Commit Task 2**

```bash
git add backend/app/sources/identity.py backend/tests/compiler/test_source_identity.py
git commit -m "fix: make structured fragment identities stable"
```

### Task 3: Store and resolve both identity layers

**Files:**
- Modify: `backend/app/sources/registry.py`
- Modify: `backend/app/sources/__init__.py`
- Modify: `backend/tests/compiler/test_source_registry.py`

**Interfaces:**
- Consumes: `Revision`, `ParsedRepresentation`, `Fragment`, and qualified `SourceRef`.
- Produces: `add_revision(revision)` and `add_representation(representation, fragments)`.
- Produces: `WorldSnapshot.current_representations: dict[str, str]`, keyed by revision ID.
- Produces: `ResolvedSource.representation`, `is_historical_revision`, `is_historical_representation`, and aggregate `is_historical`.

- [ ] **Step 1: Add failing registry coexistence and exact-resolution tests**

Build one business revision with parser v1/v2, add both, bind v2 as active, resolve v2 normally, reject v1 normally with `STALE_PARSED_REPRESENTATION`, and resolve v1 exactly with `allow_historical=True`. Add equal-content r1/r2 and snapshot-binding tests.

```python
assert resolved_v1.representation.parser_version == "json-v1"
assert resolved_v2.representation.parser_version == "json-v2"
assert resolved_v1.fragment.fragment_id != resolved_v2.fragment.fragment_id
```

- [ ] **Step 2: Run registry tests and verify RED**

Run:

```bash
uv run --project backend pytest backend/tests/compiler/test_source_registry.py -q
```

Expected: failures because the registry has no representation store or representation snapshot binding and still rejects the second parser output as a duplicate revision.

- [ ] **Step 3: Implement split registry storage and resolution**

Store revisions by ID/label, representations by ID/revision, and fragments by `(representation_id, logical_path)`. Validate representation ownership and fully qualified fragment IDs atomically before mutating registry state. Require one current representation binding for every current revision in a world snapshot.

Resolve unqualified shorthand through the snapshot's active representation. Resolve qualified refs exactly, applying stale revision and stale representation checks separately. Return only active, fully qualified refs from `allowed_refs`.

- [ ] **Step 4: Run compiler tests and verify GREEN**

Run:

```bash
uv run --project backend pytest backend/tests/compiler -q
```

Expected: all Phase A tests pass.

- [ ] **Step 5: Commit Task 3**

```bash
git add backend/app/sources/registry.py backend/app/sources/__init__.py backend/tests/compiler/test_source_registry.py
git commit -m "fix: resolve versioned parser representations"
```

### Task 4: Align canonical module documentation and verify repository gates

**Files:**
- Modify: `docs/continuum_module_01_semantic_dependency_compiler/03_ARTIFACT_INGESTION_AND_IDENTITY.md`
- Modify: `docs/continuum_module_01_semantic_dependency_compiler/08_PERSISTENCE_AND_API_CONTRACTS.md`
- Modify: `docs/continuum_module_01_semantic_dependency_compiler/12_IMPLEMENTATION_PLAN.md`
- Verify: all files changed in Tasks 1–3

**Interfaces:**
- Consumes: final identity and registry semantics.
- Produces: documentation that names `ParsedRepresentation`, qualified refs, active representation snapshot bindings, and atomic/keyed array rules.

- [ ] **Step 1: Update documentation to match implemented semantics**

Replace the three-level source hierarchy with the four-level hierarchy, document the qualified canonical grammar and percent encoding, specify array defaults and keyed strategy, and update Phase A acceptance to include parser coexistence and list insertion safety.

- [ ] **Step 2: Run diff and placeholder checks**

Run:

```bash
git diff --check
rg -n "TBD|PLACEHOLDER" backend/app/sources backend/tests/compiler docs/continuum_module_01_semantic_dependency_compiler
```

Expected: no whitespace errors and no unresolved placeholders introduced by this change.

- [ ] **Step 3: Run the full repository gate**

Run:

```bash
make test
```

Expected: backend tests, frontend tests, TypeScript compilation, and Vite production build all pass.

- [ ] **Step 4: Audit scope and commit documentation**

Stage only the three module documents plus the spec and plan; leave `AGENTS.md` unstaged.

```bash
git add docs/continuum_module_01_semantic_dependency_compiler/03_ARTIFACT_INGESTION_AND_IDENTITY.md docs/continuum_module_01_semantic_dependency_compiler/08_PERSISTENCE_AND_API_CONTRACTS.md docs/continuum_module_01_semantic_dependency_compiler/12_IMPLEMENTATION_PLAN.md docs/superpowers/specs/2026-08-19-source-identity-correction-design.md docs/superpowers/plans/2026-08-19-source-identity-correction.md
git commit -m "docs: define canonical parsed representations"
```

- [ ] **Step 5: Merge to main and push after merged-tree verification**

Fast-forward `main`, rerun `make test`, and push `main` only if `HEAD` and the verified tree match. Confirm the remote `main` SHA equals local `HEAD`.
