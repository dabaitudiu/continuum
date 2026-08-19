# 03 — Artifact Ingestion and Stable Identity

## Goal

Later invalidation only works if dependencies point to stable, versioned source identities.

## Source hierarchy

```text
Artifact
  └── Revision
       └── ParsedRepresentation
            └── Fragment
                 └── optional Span
```

## Artifact

Represents the logical object across revisions.

Fields:

```text
artifact_id              stable logical identity
artifact_type            POLICY | DOCUMENT | RECORD | TOOL_SNAPSHOT | HUMAN_APPROVAL | ...
logical_key              domain-facing stable key
owner_scope              tenant/domain/mission scope
created_at
```

Example:

```text
artifact_id = policy:security-policy
```

## Revision

Immutable snapshot.

```text
revision_id              stable unique identity
artifact_id
revision_label           v13 / commit SHA / timestamped version
content_hash
created_at
valid_from
valid_until?
source_uri?
```

Example:

```text
revision_id = policy:security-policy@revision:8fa...
revision_label = v13
```

Business revision identity is independent of content identity and parser identity. Two business labels with identical bytes remain distinct revisions, while one label cannot be silently overwritten with different bytes.

## ParsedRepresentation

Immutable parser output for one source revision.

```text
representation_id
revision_id
parser_version
parser_config_hash
created_at
```

The identity includes `revision_id`, `parser_version`, and canonical parser configuration. Parser v1 and parser v2 of the same source revision may coexist, and old provenance continues to identify its exact representation.

## Fragment

A semantically addressable subsection.

```text
fragment_id
representation_id
fragment_type            SECTION | CLAUSE | FIELD | ROW | TOOL_FIELD | PAGE_BLOCK
logical_path             e.g. section/7.3 or $.handles_customer_pii
heading?
text_hash
ordinal
parent_fragment_id?
```

### Identity rule

`fragment_id` must not depend solely on raw byte offsets because small edits shift offsets. Prefer a stable logical path when the source has structure. Use content hash + parent identity as fallback.

Example:

```text
policy:security-policy@v13!representation-id#section/7.3
vendor-profile@r7!representation-id#$.handles_customer_pii
```

Canonical references are fully representation-qualified:

```text
artifact_id @ revision_label ! representation_id # logical_path
```

Components use canonical UTF-8 percent encoding. Delimiter characters and arbitrary structured-data field names—including `@`, `#`, quotes, Unicode, slash, and `%`—therefore round-trip without ambiguity. Unqualified `artifact@revision#path` is snapshot-relative shorthand only and must not be persisted as canonical provenance.

### Structured array identity

Positional indexes are not stable identities and must not be emitted as critical fragment refs.

- Without explicit configuration, an array is one atomic fragment at its field path.
- A configured keyed array uses a unique scalar field to form selectors such as `$.controls[id="CC6.1"].result`.
- Missing, duplicate, non-scalar, or otherwise invalid stable keys fail ingestion; the parser never falls back to positions.
- The keyed-array configuration contributes to `parser_config_hash`.

## Optional span references

Use spans only for evidence display or verification:

```text
span_id
fragment_id
start_offset
end_offset
span_hash
```

Do not require permanent storage of long quoted text. Store safe excerpts only when useful for UI.

## Supported P0 source types

1. Markdown/text policy documents.
2. JSON/YAML structured records.
3. PDF converted to deterministic text blocks by a controlled parser fixture.
4. Tool snapshots returned as structured JSON.

Do not build a universal ingestion engine in this module.

## P0 normalized governing-rule contract

Reading a policy fragment is not enough to claim support for arbitrary policy logic. A governing fragment may participate in a normal accepted P0 compilation only when its active `ParsedRepresentation` exposes a versioned, trusted normalized-rule record:

```text
NormalizedRule
  normalized_rule_id         stable content-addressed identity
  obligation_key             stable within the logical policy artifact
  governing_source_ref       exact current fragment
  requirement_templates[]     reusable predicate code + subject/object roles +
                              typed context bindings + expected state + proof roles
  applicability_templates[]
  logic_form                 DIRECT_ATOM | ALL_OF | OR | THRESHOLD |
                             EXCEPTION | QUANTIFIED | UNPARSED | OTHER
  child_obligation_keys[]
  scope_qualifiers
  temporal_qualifiers
  normalized_rule_hash
```

P0 accepts only `DIRECT_ATOM | ALL_OF`. Applicable `OR`、threshold、exception、quantified or other unsupported forms produce `REJECTED_UNSUPPORTED_LOGIC`；a material rule outside the pre-registered catalog, including `NOT_EXISTS` or `EXISTS + expected_state=FALSE` absence semantics, produces `REJECTED_UNSUPPORTED_PREDICATE`。Templates are reusable domain/decision-class semantics and may not contain case IDs、exact benchmark graphs/outcomes or concrete source revisions. The compiler must never reinterpret、invent or omit them. The normalized rule must be source-authored structured policy or produced by a controlled versioned parser and independently approved/signed；unreviewed model normalization is not a trusted acceptance input.

Every in-boundary fragment is accounted exactly once in a content-addressed `RuleNormalizationManifest` as `NORMALIZED_RULES | NO_GOVERNING_RULE | UNSUPPORTED_LOGIC | UNSUPPORTED_PREDICATE | UNPARSED_REVIEW_REQUIRED`, with parser/reviewer receipts. Raw Markdown/PDF prose may still be shown as context, but missing/unreviewed normalization blocks；silent parser omission is never “no rule”。

## Artifact namespaces

Immutable identity is shared, but lifecycle/membership is not：

- `EnterpriseWorldArtifact` lives in an immutable enterprise world snapshot；
- `CompilerPolicyArtifact` lives in a separate policy snapshot；
- `CompilerDerivedArtifact` lives in the provenance store and points to its input world/universe/policy hashes；it never joins the same input world snapshot。

At minimum the following are versioned `CompilerPolicyArtifact` records：

- authority precedence policy;
- authority classification policy;
- outcome semantics policy;
- source-selection policy;
- source-universe/completeness policy;
- rule-normalization and reviewer policy;
- decision-class contract;
- predicate catalog;
- entity-binding policy;
- proof-selection policy;
- Evidence-coverage policy;
- context-partition policy;
- governed-read policy;
- upstream-Decision binding policy;
- selected-proof verification policy;
- registered cross-predicate constraint policy;
- operational limit profile;
- temporal-validity policy;
- semantic-epoch policy;
- supported-logic policy;

`SourceUniverseSnapshot` is a signed authoritative-registry snapshot envelope, not an artifact member of the world it enumerates. `DecisionProposal`/`DecisionEntityContext`/`GovernedObservationSet` are signed immutable request inputs in separate stores；they reference but are not members of the input world and do not create a fourth compiler artifact namespace. `UpstreamDecisionBinding` references a first-class Continuum Decision/envelope and never re-encodes it as an enterprise fragment. `RuleNormalizationManifest`、`SourceSetManifest`、Evidence/contradiction/selected-proof verification certificates、applicability/temporal guards、`DecisionValidityEnvelope` and `DecisionInterpretation` are compiler-derived records。

Every material agent/tool/compiler read has a signed `GovernedObservation` with tool/source identity/version、content hash、authorization context、world snapshot and executable semantic epoch. All material proposal inputs form a complete `GovernedObservationSet` under one `GovernedReadView`. Unversioned、future、mixed or bypass reads are typed input rejection and cannot become canonical proof。

## Source-universe coverage

Every compilation first binds one executable `GovernedReadView`, then a content-addressed authoritative `SourceUniverseSnapshot` containing the same epoch/world fence、owner scope、registry/catalog source、namespaces、complete artifact revisions、sync/index watermarks、snapshot hash and completeness authority. It then derives normalization and selection manifests containing exact input snapshot IDs/policy bundle ID、coverage boundaries、fragment/rule accounting、included/excluded inventories、retrieval versions、contradiction eligibility and partitions.

Required chain is `GovernedReadView → SourceUniverseSnapshot → SourceSelectionPolicy → SourceSetManifest`。A selector cannot claim completeness without a validated complete universe root. Unknown/incomplete attestation or retrieved subset causes `RUN_BLOCKED: CONTEXT_COVERAGE_INCOMPLETE`。Runtime invalidation uses selective boundary/rule/eligibility guards so unrelated inventory changes do not stale all Decisions merely because a manifest hash changed.

## Revision semantics

A compiler request is bound to a `world_snapshot_id` and executable semantic epoch/read fence. Every referenced revision must be valid in that governed snapshot, and every current revision is bound to one active parsed representation.

If trusted input references an older revision outside the declared snapshot it is input rejection. If a model emits any stale/forbidden ref outside its partition schema, the compiler attempt is `RUN_FAILED: MODEL_PROTOCOL_INTEGRITY_FAILURE` with no business disposition。

## Parser versioning

Fragment identity and parsed structure include a `ParsedRepresentation`. If parsing changes materially, re-ingest under a new parser version or parser configuration and never silently reinterpret old provenance.

## Acceptance examples

- Two revisions of the same policy share `artifact_id` but have different `revision_id`.
- Equal-content business revisions with different labels have different `revision_id` values.
- Parser v1 and parser v2 outputs for one revision coexist and resolve exactly.
- Structured JSON field references remain stable if unrelated fields are added.
- Array insertion cannot retarget an existing dependency to a different item.
- A policy edit to §12 does not change the identity of untouched §7.3 when logical headings remain stable.
- The compiler can explain exactly which revision and fragment a dependency uses.
