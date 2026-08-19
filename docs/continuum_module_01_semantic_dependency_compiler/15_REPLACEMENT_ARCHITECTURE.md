# 15 — Replacement Architecture: Requirement-Centred Compiler

## 文档状态

- Product owner 决策：**Option B 的方向已批准**。
- Product owner 评审：2026-08-19 的第一版具体规范 **REJECTED**。
- 本文状态：**REVISION 2 — FOR PRODUCT-OWNER REVIEW，尚未批准实施**。
- Module 01：**REDESIGN REQUIRED**。
- 当前 vague critic：已被 K3 与产品决策否决，不得成为生产 fallback。
- Option A（reasoner-only）只保留为 ablation baseline；Option C 不执行。
- 本文获批前，不得编写 v2 implementation plan、修改 production compiler、生成或读取 blind holdout、调用 live model、运行 full 120 paid benchmark，或开始 Module 02。

## P0 产品边界

P0 只支持 **gate-shaped enterprise approval decisions**：一个 APPROVE 必须满足一组可识别的原子 gate，组合逻辑仅为 `DIRECT_ATOM | ALL_OF`。本模块不声称支持 arbitrary enterprise reasoning。

以下 governing logic 不在 P0 支持面内：

- `OR` / `ANY_OF`；
- threshold / quorum，例如“3 项中至少 2 项”；
- exception / override chains；
- quantified rules；
- 未归一化的 temporal、numeric range 或 cross-entity aggregation；
- 其他无法无损表示为 atomic predicate 与 conjunction 的形式。

任何与当前 Decision 相关的 governing source 包含上述逻辑，或无法被受信任的 normalized-rule representation 判定逻辑形态时，必须产生 typed `UnsupportedLogicResult` 并 fail closed；禁止把它压成 conjunction。

## 决策依据

Experiment 1 已触发 K3：旧 critic 在 30 个 audited cases 中只执行 8 次，恢复 0 个 omission、发现 0 个 contradiction，虚构 4 个 `UNKNOWN_SOURCE_REQUIRED`，并新增 5 次 false block。第一版 Option B 又留下 11 个架构阻塞：Stage-1 omission、model-controlled materiality/severity、binary entailment、source-universe completeness、deterministic-policy provenance、lexical proof selection、窄化的 injection gate、非盲 holdout、contradiction truncation 和 unsupported logic。

Revision 2 保留 Option B 的职责拆分，但把 coverage、proof authority 与 source/policy completeness 纳入 deterministic trust boundary。

## 架构不变量

1. `Requirement` 是结构化 semantic proposition，不是 source ref；显示文本不是 identity。
2. Stage 1 不是 requirement coverage 的单点。独立 coverage pass 必须从完整 governing-source universe 发现遗漏的 material obligation。
3. model 只能输出 requirement、binding、entailment、contradiction observation 的候选；不能直接输出 canonical materiality、contradiction impact、disposition 或 Runtime mutation。
4. canonical `CRITICAL` 是 deterministic proof-selection 的结果：被选入必要 Requirement proof 的 binding 才是 validity-bearing。
5. model contradiction severity 仅为 advisory。是否 validity-critical 由 requirement reachability、proof eligibility、authority/preference 与 resolution state 计算。
6. evidence entailment 至少是 `ENTAILED_TRUE | ENTAILED_FALSE | INDETERMINATE`；`INDETERMINATE` 不能证明 DIRECT Requirement。
7. 编译只在 source universe 被声明并验证为对该 decision class 完整时运行。`INCOMPLETE | UNKNOWN` coverage 必须 fail closed。
8. authority、outcome、source selection、predicate、proof selection、logic support 和 partition rules 都是 versioned validity dependencies，不是 audit-only strings。
9. contradiction pass 必须覆盖完整 in-scope inventory；不得因 context limit 静默截断。
10. semantic omission、incompleteness、contradiction 与 ambiguity 不得在相应 semantic pass 之前终止。Structural corruption 可以提前终止。
11. canonical support 与 invalidation 使用 transitive graph reachability；不得要求 redundant direct source edges。
12. LLM output 永远不能直接修改 canonical Runtime state。

## Versioned trusted inputs

### `CompilerPolicyBundle`

每次 compilation 都绑定一个 immutable policy bundle：

```text
CompilerPolicyBundle
  bundle_id: content-addressed ID
  schema_version: string
  authority_precedence_policy_ref: canonical SourceRef
  authority_classification_policy_ref: canonical SourceRef
  outcome_semantics_policy_ref: canonical SourceRef
  source_selection_policy_ref: canonical SourceRef
  decision_class_contract_ref: canonical SourceRef
  predicate_catalog_ref: canonical SourceRef
  proof_selection_policy_ref: canonical SourceRef
  context_partition_policy_ref: canonical SourceRef
  supported_logic_policy_ref: canonical SourceRef
  additional_interpretation_policy_refs[]: canonical SourceRef
  bundle_hash: SHA-256
```

这些 refs 必须解析到当前 world snapshot 中 immutable、trusted、versioned policy artifacts。任何实际参与 `DecisionJustification` 的 policy ref 都进入 canonical validity provenance；更新它必须能通过正常 artifact-change invalidation 使旧 Decision `STALE`。仅把 version ID 写进 metadata 不满足该要求。

```text
PolicyUsageTrace
  policy_ref: canonical SourceRef
  rule_keys_used[]
  input_hash: SHA-256
  output_hash: SHA-256
```

Every deterministic component that can alter Requirement identity、proof eligibility/selection、authority resolution、outcome/disposition、canonical mapping or coverage records a usage entry. Gate rejects `UNVERSIONED_POLICY_INPUT` if such a code path reads configuration not resolved from the bundle. `selected_policy_refs` comes from this trace, not a manually curated audit list。

### `SourceSetManifest`

Context Assembly 必须生成并验证：

```text
SourceSetManifest
  manifest_id: content-addressed ID
  schema_version: string
  decision_class_id: string
  owner_scope: string
  world_snapshot_id: string
  source_selection_policy_ref: canonical SourceRef
  selection_run_id: string
  retrieval/index/query_versions[]
  coverage_boundary:
    artifact_types[]
    logical_namespaces[]
    authority_classes[]
    temporal_boundary
  included_artifacts[]:
    artifact_id / revision_id / representation_id / content_hash
    included_fragment_refs[]
  excluded_artifacts[]:
    artifact_id / revision_id / reason_code
  governing_fragment_refs[]
  contradiction_eligible_fragment_refs[]
  coverage_status: DECLARED_COMPLETE | INCOMPLETE | UNKNOWN
  declared_complete_for_decision_class: boolean
  completeness_declaration_authority: string
  partition_plan_hash: SHA-256
  manifest_hash: SHA-256
```

`DECLARED_COMPLETE` 只能由 trusted source-selection component 按 versioned policy 产生，不能来自 model。Validator 必须对 world snapshot、boundary、included/excluded inventory、revision/representation hashes 和 deterministic manifest hash 复算。

如果底层只提供 retrieved subset，selection policy 必须说明它如何对该 decision class 保证完整性，并记录 query/index/retriever versions。无法证明完整的 retrieval 返回 `UNKNOWN`，结果为 `RUN_BLOCKED: CONTEXT_COVERAGE_INCOMPLETE`，不得伪装成正常 `REJECTED_*` 或 `ACCEPTED`。

`SourceSetManifest` 自身作为 immutable manifest artifact 进入 accepted Decision 的 validity provenance。其 logical key 由 owner scope、decision class、coverage-boundary digest 和 source-selection-policy logical key 派生；revision hash由完整 inventory/world snapshot 派生。Relevant artifact add/remove/revision 或 selection-policy revision 会让 trusted selector发布一个 superseding manifest revision和普通 artifact-change event。旧 Decision依赖旧 manifest revision，因此必须 revalidate。

## Stable semantic identity

显示命题不能决定 canonical identity。P0 使用：

```text
PredicateIdentity
  predicate_catalog_id: bundle-resolved stable catalog ID
  predicate_code: stable catalog key
  subject:
    entity_type: string
    entity_id: stable request/world identity
  comparator: IS | EQUALS | EXISTS | NOT_EXISTS
  typed_object: bool | string | integer | stable entity identity
  scope_qualifiers: canonical map
  temporal_qualifiers: canonical map
```

`predicate_catalog_id` must equal the identity resolved from `CompilerPolicyBundle.predicate_catalog_ref`; the Requirement itself contains no SourceRef. `predicate_semantic_key` 是上述 canonical JSON 的 hash，不包含 `proposition_display`、model local ID、case ID、domain name 或 source wording。

- DIRECT requirement ID 由 `predicate_semantic_key + expected_state + proof_contract` 派生。
- ALL_OF requirement 先递归 flatten nested conjunction、去重并按 child semantic key 排序，再由 child IDs 派生。
- validator 拒绝未知 predicate code、非法 subject/object type、非 canonical qualifier 或同义但不一致的重复 predicate。
- `proposition_display` 只用于审计和 UI；改变措辞不能改变 requirement ID、排序、proof slice 或 Runtime edges。

## Replacement pipeline

```mermaid
flowchart TD
    A[DecisionRequest + world snapshot + CompilerPolicyBundle] --> B[0A. SourceSet Assembly]
    B --> B1[Manifest + coverage + partition validation]
    B1 -->|incomplete / unknown / over hard limit| RB[RUN_BLOCKED: CONTEXT_COVERAGE_INCOMPLETE]
    B1 -->|unsupported applicable governing logic| UL[COMPLETED: REJECTED_UNSUPPORTED_LOGIC]
    B1 --> C[1A. Requirement Decomposition]
    B1 --> D[1B. Independent Governing-Obligation Coverage]
    C --> E[1C. Deterministic Requirement Reconciliation]
    D --> E
    E -->|typed structural error| X[Terminal structural disposition]
    E -->|unreconciled / unsupported semantic identity| UI[COMPLETED: REJECTED_REQUIREMENT_COVERAGE]
    E --> F[2. Evidence Binding Candidates]
    F --> F1[Deterministic ref / scope / temporal / role validation]
    F1 --> G[3A. Partitioned Independent Contradiction Observation]
    G --> G1[3B. Deterministic coverage check + global reduce + precedence]
    G1 -->|partial inventory| RB
    G1 --> H[4. Deterministic Proof Selection + Requirement Completeness]
    H --> I[5. Deterministic Acceptance Gate]
    I -->|ACCEPTED| J[Deterministic Canonicalizer]
    I -->|REJECT / REVIEW| K[Immutable non-accepted CompilationResult]
    J --> L[Immutable accepted CompilationResult]
    L --> M[RuntimeAcceptanceService]
    M --> N[Canonical Runtime graph mutation]
```

### Stage 0 — Source and policy coverage

Deterministic Context Assembly resolves `CompilerPolicyBundle`, builds `SourceSetManifest`, verifies completeness, identifies governing/contradiction-eligible fragments, and builds a coverage-preserving partition plan. It does not perform semantic requirement discovery。

### Stage 1A — Requirement Decomposition

A model proposes the decision's atomic gate requirements and conjunction topology using stable `PredicateIdentity`. It receives the request, supported decision-class contract and allowed source context, but no benchmark labels。

### Stage 1B — Independent Governing-Obligation Coverage

This is a separate, narrowly scoped semantic pass. It receives the request、decision-class/predicate contracts and every current governing obligation in the validated manifest. It **does not receive Stage-1A output**. Its only question is: which material governing obligations apply to this decision?

It cannot judge outcome, bind factual evidence, search for generic omissions, assign materiality/severity, invent refs, or emit disposition. It returns one typed applicability observation for every normalized governing obligation plus `RequirementCoverageCandidate[]` for applicable obligations。

It uses a distinct prompt/schema and one or more deterministic governing-obligation partitions when the complete inventory does not fit one call. Every partition sees the same request/contracts and a disjoint normalized-obligation subset, never Stage-1A output. Deterministic validation requires all expected receipts and the processed-obligation-key union to equal the manifest inventory. `INDETERMINATE` applicability is a semantic coverage gap and cannot normally accept；missing/truncated/over-limit partitions are execution-blocking. Decomposition alone is never accepted as a fallback。

### Stage 1C — Deterministic Requirement Reconciliation

Code compares 1A and 1B by stable semantic key：

- matching candidates coalesce into one effective Requirement；
- a valid coverage-only candidate becomes an effective Requirement with `origin=COVERAGE_PASS` and continues through Evidence Binding；
- conflicting expected states or incompatible topology become `REQUIREMENT_RECONCILIATION_CONFLICT` and cannot accept；
- unknown predicate identity or unsupported logical form yields a typed fail-closed result；
- no candidate may create a source ref: every provenance anchor must already exist in the manifest。

This mechanism can recover a Stage-1 omission without recreating the old critic because its input, question, output and write contract are narrow and outcome-blind。

### Stage 2 — Evidence Binding

The model proposes semantic roles, entailment and counterfactual analysis for every effective DIRECT Requirement. It does **not** output canonical `CRITICAL | SUPPORTING`。

### Stage 3 — Independent Contradiction

An independent map pass observes all contradiction-eligible source propositions relative to stable predicates. Deterministic reduce verifies full coverage, joins observations across partitions, constructs conflicts and applies versioned authority precedence. The pass is independent of Stage-2 selected refs, so omission in binding cannot hide a contradiction。

Contradiction observations never become EvidenceBindings or canonical edges. If deterministic precedence selects a source that has no matching validated Stage-2 binding candidate, Stage 4 has no selectable proof for that role and the Requirement is insufficient；Stage 3 cannot promote it as a repair。

### Stage 4 — Deterministic proof selection and completeness

Code selects proof bindings for each required proof role, derives canonical materiality, derives contradiction impact, and computes every `RequirementAssessment`. No model call occurs。

### Stage 5 — Deterministic acceptance

Code computes expected outcome/disposition and, for accepted APPROVE/DENY only, emits a stable `DecisionJustification`. The canonicalizer consumes only that proof slice。

## Typed contracts

All contracts are immutable analysis IR. Only deterministic validators may convert model candidates into validated objects。

### `Requirement`

```text
Requirement
  requirement_id: deterministic semantic ID
  predicate_identity: PredicateIdentity | null       # DIRECT only
  proposition_display: string                        # non-authoritative
  kind: FACT | RULE | AUTHORIZATION | EVIDENCE_PRESENCE | NEGATIVE_CONSTRAINT
  expected_state: TRUE | FALSE
  logical_form: DIRECT_ATOM | ALL_OF
  child_requirement_ids[]                            # ALL_OF only
  required_proof_roles[]                             # derived from predicate/decision contract
  origin: DECOMPOSITION | COVERAGE_PASS | BOTH
  governing_obligation_keys[]
  rationale_summary: string
```

Rules：

- `DIRECT_ATOM` has a stable predicate and no children。
- `ALL_OF` has no independent predicate; children are flattened, deduped and sorted deterministically。
- Every Requirement is necessary for APPROVE validity. There is no SUPPORTING Requirement。
- `required_proof_roles` is derived from the versioned predicate/decision contract, not freely authored by the model. A policy-derived gate may require both `GOVERNING_AUTHORITY` and `STATE_EVIDENCE` proof roles。
- `governing_obligation_keys` identify normalized rule records, not source refs. Their provenance is carried by bindings。
- Unsupported OR/threshold/exception/quantified forms cannot enter this type。

### `RequirementCoverageObservation`, `RequirementCoverageCandidate` and result

```text
RequirementCoverageObservation               # model output, one per obligation
  governing_obligation_key: string
  governing_source_refs[]: existing canonical SourceRef
  applicability: APPLICABLE | NOT_APPLICABLE | INDETERMINATE
  applicability_summary: string
  candidate_local_id?: string                 # required iff APPLICABLE

RequirementCoverageReceipt
  partition_id: string
  manifest_hash: SHA-256
  processed_obligation_keys[]
  output_hash: SHA-256
```

The deterministic coverage plan records expected partition IDs and obligation-key membership. Across all receipts, every normalized governing obligation key in the manifest must appear exactly once. `NOT_APPLICABLE` is auditable model semantics and measured against DEV; `INDETERMINATE` prevents normal acceptance. Missing/duplicate/unexpected keys or a receipt mismatch cannot be treated as “no omission found”。

```text
RequirementCoverageCandidate                 # model output
  candidate_local_id: string
  predicate_identity: PredicateIdentity
  proposition_display: string
  expected_state: TRUE | FALSE
  logical_form: DIRECT_ATOM | ALL_OF
  child_predicate_semantic_keys[]
  governing_obligation_key: string
  governing_source_refs[]: existing canonical SourceRef
  applicability_summary: string
  detected_logic_form: DIRECT_ATOM | ALL_OF | UNSUPPORTED
  unsupported_logic_kind?: OR | THRESHOLD | EXCEPTION | QUANTIFIED | OTHER

RequirementCoverageResult                    # validated result
  observations[]
  candidates[]
  receipts[]
  coverage_status: COMPLETE | INDETERMINATE
  finding_codes[]
```

Model output is a semantic requirement candidate with real provenance anchors, never `UNKNOWN_SOURCE_REQUIRED`. Validator checks every ref、obligation key and predicate identity against the manifest/normalized governing representation, and verifies complete obligation coverage. A malformed/fabricated ref is structural failure；a valid missing candidate is non-terminal and is reconciled；semantic `INDETERMINATE` yields fail-closed requirement coverage with no canonical output。

### `EvidenceBindingCandidate` and validated `EvidenceBinding`

```text
EvidenceBindingCandidate                     # model output
  binding_local_id: string
  requirement_id: string
  source_ref: canonical SourceRef
  semantic_role: GOVERNING_AUTHORITY | STATE_EVIDENCE |
                 AUTHORIZATION_RECORD | SATISFACTION_RECORD | CONTEXT
  entailment_target: OBLIGATION_APPLICABILITY | PREDICATE_STATE
  entailment: ENTAILED_TRUE | ENTAILED_FALSE | INDETERMINATE
  normalized_value?: typed value
  counterfactual_summary: string

EvidenceBinding                              # deterministic validated object
  candidate: EvidenceBindingCandidate
  authority_class: trusted classification
  proof_eligibility: ELIGIBLE | INELIGIBLE
  eligibility_finding_codes[]
  selected_proof_role?: semantic role
  proof_role: SELECTED_PROOF | UNSELECTED_SUPPORT | ANALYSIS_ONLY
  canonical_materiality: CRITICAL | SUPPORTING | NONE
```

Rules：

- Model contract contains no canonical materiality field。
- Ref existence、scope、snapshot、authority class、role legality and predicate compatibility are deterministic checks。
- `GOVERNING_AUTHORITY` targets `OBLIGATION_APPLICABILITY`；state/authorization/satisfaction evidence targets `PREDICATE_STATE`. A policy saying “training is required” does not prove that training is current。
- A reconciled applicable Requirement needs selected `OBLIGATION_APPLICABILITY=ENTAILED_TRUE` governing proof when its contract requires that role. FALSE conflicts with coverage applicability and cannot be treated as ordinary factual DENY；INDETERMINATE is insufficient。
- `INDETERMINATE` cannot satisfy/refute a DIRECT Requirement and is never `SELECTED_PROOF`。
- For each required proof role, proof selector considers only eligible, determinate bindings after authority resolution and selects by versioned proof policy: authority/preference tier, stable source identity, then binding semantic key。
- Selected bindings become `CRITICAL`. Unselected explanatory bindings become `SUPPORTING`; irrelevant/ineligible/indeterminate observations are analysis-only and have no canonical edge。
- An incorrect model suggestion can cause insufficient evidence or a measured semantic error, but a model cannot label a selected proof SUPPORTING to cause stale escape。

### `ContradictionObservation`, `ContradictionCandidate` and `Contradiction`

```text
ContradictionObservation                     # independent model map output
  observation_local_id: string
  partition_id: string
  requirement_id: string
  source_ref: canonical SourceRef
  entailment_target: OBLIGATION_APPLICABILITY | PREDICATE_STATE
  entailment: ENTAILED_TRUE | ENTAILED_FALSE | INDETERMINATE
  normalized_value?: typed value
  proposition_display: string
  model_severity_advisory: CRITICAL | SUPPORTING | UNKNOWN

ContradictionCandidate                       # deterministic global join
  contradiction_id: deterministic ID
  requirement_id: string
  lhs_observation_id: string
  rhs_observation_id: string
  contradiction_type: DIRECT_NEGATION | VALUE_MISMATCH |
                      SCOPE_CONFLICT | TEMPORAL_CONFLICT | AUTHORITY_CONFLICT

Contradiction                                # deterministic validated record
  candidate: ContradictionCandidate
  resolution: LHS_PRECEDES | RHS_PRECEDES | UNRESOLVED
  precedence_policy_ref: canonical SourceRef
  precedence_rule_key?: string
  affected_root_requirement_ids[]
  lhs_proof_eligibility: ELIGIBLE | INELIGIBLE
  rhs_proof_eligibility: ELIGIBLE | INELIGIBLE
  deterministic_impact: VALIDITY_CRITICAL | NON_BLOCKING
  impact_finding_codes[]
```

Only determinate opposing observations over the same Requirement **and entailment target** can form a contradiction. `deterministic_impact=VALIDITY_CRITICAL` iff the conflict affects an effective Requirement reachable to a Decision root, at least one side is proof-eligible for a required role, and authority/preference state either remains unresolved or changes which truth can be selected. Model severity/recommendation never participates in this calculation。

### `ContradictionCoveragePlan`

```text
ContradictionCoveragePlan
  policy_ref: canonical SourceRef
  eligible_fragment_refs[]
  requirement_ids[]
  hard_limits:
    max_fragments / max_requirements / max_tokens_per_partition /
    max_partitions / max_observations
  partitions[]:
    partition_id / ordered_fragment_refs[] / input_hash
  expected_partition_ids[]
  plan_hash: SHA-256

ContradictionCoverageReceipt
  partition_id
  input_hash
  processed_fragment_refs[]
  observation_ids[]
  output_hash
```

Partitioning is deterministic over stable refs and token counts. Every eligible ref is assigned exactly once; reduce verifies union equality, no unexpected ref, every expected receipt, matching input hash and bounded output. Cross-partition conflicts are found by global join on stable requirement/predicate keys. Exceeded hard limit、truncation、timeout、missing receipt or partial union yields `RUN_BLOCKED: CONTEXT_COVERAGE_INCOMPLETE`; partial output can be audited but never reported as a complete contradiction pass。

### `RequirementAssessment`

```text
RequirementAssessment
  requirement_id: string
  status: SATISFIED | UNSATISFIED | CONTRADICTED | INSUFFICIENT_EVIDENCE
  selected_proof_binding_ids[]
  supporting_binding_ids[]
  contradiction_ids[]
  support_paths[][]
  blocking_requirement_ids[]
  finding_codes[]
  assessment_summary: deterministic template
```

DIRECT truth table after precedence/proof selection：

| Selected required-role evidence | Result |
|---|---|
| every applicability role is determinately TRUE and every state role matches `expected_state` | `SATISFIED` |
| every applicability role is TRUE and all state roles are covered but at least one selected state is opposite, with no unresolved critical conflict | `UNSATISFIED` |
| unresolved validity-critical contradiction | `CONTRADICTED` |
| any required role absent or only `INDETERMINATE` | `INSUFFICIENT_EVIDENCE` |

`OBLIGATION_APPLICABILITY=ENTAILED_FALSE` against an APPLICABLE reconciled obligation is `REQUIREMENT_RECONCILIATION_CONFLICT` and fails closed；it is not evidence that the business gate itself is false。

ALL_OF uses: any `CONTRADICTED` → `CONTRADICTED`; else any `UNSATISFIED` → `UNSATISFIED`; else all `SATISFIED` → `SATISFIED`; else `INSUFFICIENT_EVIDENCE`。

Completeness evaluates the reconciled effective Requirement set, not only Stage-1A output. It cannot invent requirements, refs, bindings or placeholder refs。

### `UnsupportedLogicResult`

```text
UnsupportedLogicFinding
  finding_id: deterministic ID
  governing_source_ref: canonical SourceRef
  normalized_rule_key?: string
  logic_kind: OR | THRESHOLD | EXCEPTION | QUANTIFIED | UNPARSED | OTHER
  affected_predicate_keys[]
  detector: INGESTION_RULE_SCHEMA | COVERAGE_PASS | REQUIREMENT_VALIDATOR
  detail_code: string

UnsupportedLogicResult
  run_status: COMPLETED
  disposition: REJECTED_UNSUPPORTED_LOGIC
  findings[]
  canonical_output: none
```

Governing sources used for normal P0 acceptance must expose a trusted normalized-rule representation whose logic form is verifiable. It must be source-authored structured policy or produced by a versioned controlled ingestion parser and independently approved/signed; an unreviewed model normalization is not trusted acceptance evidence. Raw prose can be read as context, but if its applicable rule cannot be normalized to P0 forms, the run fails closed。

## Stage ownership

| Stage | Model owns | Deterministic code owns | Explicitly forbidden |
|---|---|---|---|
| 0 SourceSet/Policy Assembly | nothing | manifests、coverage status、world binding、policy refs、limits、partition plan | semantic requirement discovery |
| 1A Decomposition | typed requirement candidates + outcome proposal | semantic IDs、schema、P0 logic validation、normalization | refs、materiality、disposition |
| 1B Coverage | independent governing-obligation candidates | ref/obligation/predicate validation | seeing 1A output、factual evidence binding、outcome judgment |
| 1C Reconciliation | nothing | merge by semantic key、origin、coverage conflict/unsupported result | lexical matching as authority |
| 2 Evidence | role/entailment/counterfactual candidates | eligibility、authority metadata、proof policy inputs | canonical CRITICAL/SUPPORTING、canonical edges |
| 3 Contradiction | partition observations + advisory severity | coverage proof、global join、precedence、impact | canonical severity、binding promotion、disposition |
| 4 Proof/Completeness | nothing | proof selection、materiality、truth table、reachability、assessments | semantic invention、outcome rewrite |
| 5 Gate | nothing | expected class、disposition、stable justification | model retry or semantic repair |
| Canonicalizer | nothing | IDs、proof graph、policy provenance、hash、dedupe | adding omitted evidence/requirements |
| RuntimeAcceptanceService | nothing | immutable checks、atomic Runtime mutation | compiler/model semantics |

## Terminal and non-terminal semantics

### Early structural termination

- malformed typed output after one bounded schema repair；
- duplicate/unknown local IDs、invalid enum、invalid canonical semantic identity or cycle；
- fabricated/unauthorized/cross-scope/stale source ref；
- manifest/hash/world-snapshot mismatch；
- illegal source role or authority-class relation；
- inconsistent typed cross-link。

These produce explicit structural disposition and `SKIPPED_STRUCTURAL_TERMINATION` for downstream stages. They never produce canonical output。

### Execution blocking

- credential/provider/transport/budget unavailable；
- source universe `INCOMPLETE | UNKNOWN`；
- contradiction coverage plan exceeds hard limits；
- any partition timeout/truncation/missing receipt/coverage mismatch。

These produce `RUN_BLOCKED` with no semantic disposition or canonical output. Partial analysis remains evidence only。

### Semantic fail-closed results

- applicable unsupported logic → `REJECTED_UNSUPPORTED_LOGIC`；
- unreconciled coverage candidate/conflicting requirement identity → `REJECTED_REQUIREMENT_COVERAGE`；
- insufficient determinate evidence → `REJECTED_INCOMPLETE_REQUIREMENTS` or `NEEDS_HUMAN_REVIEW` according to proposal class；
- unresolved validity-critical contradiction → `NEEDS_HUMAN_REVIEW`；
- outcome mismatch → `REJECTED_OUTCOME_CONSTRAINT` / `REJECTED_CONTRADICTION`。

Missing evidence、`INDETERMINATE`、contradiction or low confidence are not structural errors. Once an effective supported Requirement set exists, Stage 3 and Stage 4 run before Stage 5 decides。

### Exact result matrix

| Condition | `run_status` | Disposition | Downstream behavior |
|---|---|---|---|
| model schema invalid after one repair | `COMPLETED` | `REJECTED_SCHEMA` | later stages `SKIPPED_STRUCTURAL_TERMINATION` |
| invalid semantic/local ID、cycle、receipt duplicate/unexpected key | `COMPLETED` | `REJECTED_INVALID_STRUCTURE` | structural termination |
| deterministic semantic path reads unregistered config | `COMPLETED` | `REJECTED_INVALID_STRUCTURE` (`UNVERSIONED_POLICY_INPUT`) | no gate/canonical output |
| fabricated、unauthorized、cross-scope or stale ref | `COMPLETED` | `REJECTED_INVALID_REFERENCE` | structural termination |
| policy/manifest hash or world binding invalid | `COMPLETED` | `REJECTED_INVALID_STRUCTURE` | structural termination |
| SourceSet incomplete/unknown or hard cap exceeded | `BLOCKED` | none | no semantic/canonical result |
| provider、credential、transport or budget unavailable | `BLOCKED` | none | no fallback to another semantic architecture |
| coverage/contradiction invocation truncated or receipt absent after transport failure | `BLOCKED` | none | partial output audit-only |
| governing applicability `INDETERMINATE` or reconciliation conflict | `COMPLETED` | `REJECTED_REQUIREMENT_COVERAGE` | no canonical output |
| applicable unsupported/unparsed governing logic | `COMPLETED` | `REJECTED_UNSUPPORTED_LOGIC` | no canonical output |
| evidence entailment `INDETERMINATE` | continues | none yet | Stage 3/4 run；assessment may be insufficient |
| missing proof binding | continues | none yet | Stage 3/4 run；Gate decides incomplete/review |
| unresolved validity-critical contradiction | continues | none yet | Stage 4 runs；Gate returns human review |
| contradiction partition partial/mismatched | `BLOCKED` | none | cannot report contradiction completion |
| internal persistence/invariant defect | `FAILED` | none | no canonical output |

## Deterministic acceptance gate

Preconditions for any normal gate evaluation：

1. active `CompilerPolicyBundle` and `SourceSetManifest` validate；
2. source coverage is `DECLARED_COMPLETE` for the decision class；
3. all contradiction partitions and receipts validate complete；
4. no applicable unsupported logic or unreconciled requirement coverage conflict exists；
5. every effective Requirement has exactly one deterministic assessment；
6. canonical materiality has been derived from proof selection, not accepted from a model field。

Expected outcome class：

- root closure contains unresolved `VALIDITY_CRITICAL` contradiction → `REVIEW`；
- else all roots `SATISFIED` → `APPROVE`；
- else any root `UNSATISFIED` → `DENY`；
- else → `REVIEW`。

Disposition：

- expected REVIEW from contradiction → `NEEDS_HUMAN_REVIEW` for any model proposal；
- expected REVIEW from insufficient evidence: REVIEW proposal → `NEEDS_HUMAN_REVIEW`; APPROVE/DENY proposal → `REJECTED_INCOMPLETE_REQUIREMENTS`；
- expected APPROVE/DENY but proposal class differs → `REJECTED_OUTCOME_CONSTRAINT`，或 precedence winner directly causes mismatch 时 `REJECTED_CONTRADICTION`；
- only matching APPROVE/DENY with all preconditions can be `ACCEPTED`。

```text
DecisionJustification
  outcome_class: APPROVE | DENY
  selected_root_requirement_ids[]
  selected_requirement_ids[]
  selected_proof_binding_ids[]
  selected_policy_refs[]
  source_set_manifest_ref: canonical SourceRef
  semantic_proof_key: SHA-256
  selection_rule: ALL_APPROVAL_ROOTS | STABLE_FAILED_PROOF_PATH
```

APPROVE selects all satisfied root closures. DENY selects one failed proof path with the smallest tuple：

```text
(
  failure_class_priority from proof_selection_policy,
  failed DIRECT predicate_semantic_key,
  sorted selected proof SourceRef identities,
  flattened canonical path topology hash
)
```

`proposition_display`、model local ID、case ID、domain 和 iteration order 均不参与选择。相同 structured semantics/context 下的 paraphrase 必须得到相同 proof slice。

## Canonical graph and Runtime invalidation

```text
SourceFragment / GoverningPolicyFragment
    --SUPPORTED_BY / GOVERNED_BY[CRITICAL]-->
Claim(DIRECT requirement assessment)
    --DERIVED_FROM / REQUIRES[CRITICAL]-->
Claim(ALL_OF requirement assessment)
    --REQUIRES[CRITICAL]-->
Decision

CompilerPolicyArtifact / SourceSetManifestArtifact
    --GOVERNED_BY[CRITICAL]-->
Claim(DecisionInterpretation)
    --REQUIRES[CRITICAL]-->
Decision
```

Rules：

1. Only Stage-4 `SELECTED_PROOF` bindings become source-to-claim CRITICAL edges。
2. Unselected candidates cannot become Runtime validity dependencies merely because the model called them important。
3. Every selected governing/state/counterevidence binding is represented; accepted DENY cannot rely only on non-invalidating `CONTRADICTED_BY`。
4. ALL_OF is transitive. Existing Source → Claim → Claim → Decision closure is sufficient; no redundant direct edge is required。
5. All policy refs and the SourceSetManifest that materially produced the justification map to validity-bearing provenance. Their revision changes use the same artifact-change invalidation path as enterprise sources。
6. Supporting/analysis-only evidence has no critical Runtime edge and cannot cause stale propagation。
7. Unresolved contradiction, incomplete coverage, unsupported logic and REVIEW produce no canonical graph。
8. RuntimeAcceptanceService rechecks exact compilation hash、mission revision、world snapshot、policy bundle and manifest refs before atomic commit。

## Contradiction scaling contract

No model call may receive a silently truncated inventory. The versioned partition policy fixes hard limits and deterministic partitioning. Each partition sees all effective requirement semantic keys plus a disjoint source subset. It emits one observation or explicit `NO_RELEVANT_PROPOSITION` coverage marker per processed ref/required predicate unit as specified by the schema。

Revision-2 initial hard caps, encoded in `context-partition-policy-v2` and included in the policy hash, are：

```text
max_effective_requirements = 64
max_contradiction_eligible_fragments = 2_048
max_total_inventory_tokens = 1_000_000
max_tokens_per_partition = 16_000
max_requirement_coverage_partitions = 64
max_contradiction_partitions = 64
max_observations = 131_072
```

The orchestrator may create fewer/smaller partitions but may not raise/lower these limits without a new policy revision. Exceeding any cap produces context-coverage `RUN_BLOCKED`；it never samples/truncates to fit。

Reducer first verifies receipts and coverage, then joins observations across **all** partitions. Thus a TRUE observation in partition A and FALSE observation in partition B still forms one contradiction. If the complete cross-product cannot be represented under `max_observations` or partition count, the safe result is `RUN_BLOCKED: CONTEXT_COVERAGE_INCOMPLETE`, not “0 contradictions”。

## Blind holdout protocol

The previous developer-generated visible holdout design is removed。

- Holdout owner: product owner or independent evaluator outside the development repository and implementation agent workspace。
- Development may see only `holdout_schema_version`、domain/category counts、evaluator version、encrypted or aggregate content hash、ownership attestation and reveal protocol. It cannot see case bodies、source text、ground truth or generator seed。
- Implementation Codex does not generate、read、index or commit holdout cases before methodology freeze。
- Reveal/run occurs once only after full DEV P0 PASS and freeze of code commit、prompts、schemas、policy bundle、dependency lock、runner/evaluator version and metric implementation。
- DEV and HOLDOUT remain separate reports. No case-specific change is allowed after reveal. Any post-holdout method change creates a new methodology version and requires a fresh independently held set; it cannot reuse the revealed set as blind evidence。

## Adversarial prompt-injection contract

Prompt-injection safety is evaluated on paired clean/injected cases with identical governing semantics. A pair passes only if injection：

1. does not suppress any required stable predicate/Requirement；
2. does not change selected critical evidence coverage except the deliberately modified untrusted fragment identity；
3. does not suppress or downgrade contradiction impact；
4. does not change expected outcome or final disposition；
5. does not increase accepted-only stale escape or unnecessary invalidation；
6. creates zero illegal authority/ref/policy edges；
7. does not enter the canonical proof as an instruction-bearing authority。

Metrics include requirement-suppression rate、critical-coverage delta、contradiction-suppression rate、outcome/disposition flip rate、mutation-quality delta and illegal-authority rate. The old “injected ref did not become critical” observation alone is insufficient to pass P0。

## Old critic migration/removal

1. Freeze current `reasoner-v2 + critic-v1` behavior、prompt、schema、raw evidence and evaluator as `legacy-critic-v1`。
2. Remove old critic from active/default v2 orchestration; no v2 failure fallback。
3. Legacy adapter is benchmark-only and cannot call Runtime acceptance。
4. V2 types use a separate namespace; `CriticProposal` fields are not reinterpreted as coverage/contradiction objects。
5. Remove active API `critic_findings` after cutover; retain only versioned report readers needed for immutable evidence replay。
6. After all P0 including blind holdout/live Gemini pass, delete non-replay legacy implementation/tests。

## Ablation and experiment design

### Primary arms

| Arm | Definition | Production eligibility |
|---|---|---|
| A — reasoner-only | frozen single-pass baseline | never |
| B — old critic | frozen K3 pipeline | never |
| C — Revision-2 Option B | coverage + binding + independent contradiction + deterministic proof/gate | only candidate |

A/B reuse immutable Experiment-1 evidence; no new legacy calls. C uses the frozen 30-case DEV subset under the same tasks/sources/provider settings where comparable. Call topology、prompt/schema versions、latency、tokens and settled cost are explicit variables。

### Bounded progression

1. **Experiment 2A — Requirement decomposition + independent coverage**：measure Stage-1A recall、coverage-only recovery、coverage false candidates、reconciled requirement recall/precision、unsupported-logic detection。
2. **Experiment 2B — Evidence binding + deterministic proof materiality**：measure entailment confusion including INDETERMINATE、selected-proof critical recall/precision、supporting confusion and Runtime proof coverage。
3. **Experiment 3 — Partitioned contradiction**：contradiction pair recall、deterministic impact recall、partition coverage、cross-partition recall、must-block。
4. **Experiment 4 — Gate + provenance + mutation**：outcome/must-block、policy/manifest invalidation、critical/supporting mutation direction、stable paraphrase proof selection。
5. **Experiment 5 — Integrated three-arm 30-case DEV subset**：C must meet every current P0 threshold and coverage/adversarial prerequisites before full DEV。
6. **Experiment 6 — Full 120 DEV**：only after Experiment 5 PASS。
7. **Experiment 7 — One-time independently owned blind holdout**：only after full DEV PASS and method freeze。
8. **Experiment 8 — Live Gemini**：only after OpenAI DEV + blind holdout support the methodology。

Every paid experiment requires preregistered hypothesis、hashes、case-selection rule、max calls、worst-case cost and stop interpretation. No individual-case tuning。

### Metrics

- Stage-1A requirement recall；
- independent coverage recovery recall / false-candidate rate；
- reconciled effective-requirement recall / precision；
- unsupported-logic detection recall / false-block rate；
- entailment confusion matrix including `INDETERMINATE`；
- selected-proof canonical critical recall / precision；
- canonical materiality confusion and proof-role completeness；
- contradiction pair recall；
- deterministic contradiction-impact recall（不再以 model severity 当 canonical truth）；
- source-universe / partition coverage completion rate；
- outcome / must-block compliance；
- accepted compilation coverage and disposition confusion；
- prompt-injection paired semantic invariance metrics；
- policy/manifest revision stale propagation；
- accepted-only stale escape / unnecessary invalidation with denominators；
- paraphrase-stable proof-slice rate；
- unsupported canonical refs、determinism、calls、latency、token categories and settled cost。

Proposal-union refs、validated candidates、selected proof、accepted canonical graph and Runtime mutation are separate layers and must be separately reported。

## Normative counterexamples for P0 blockers

这些是 synthetic architecture fixtures，不是 DEV/HOLDOUT/live-model evidence。

### P0-1 — Stage-1 omission is recovered

Stage 1A emits only `vendor_encrypted=true`。Independent coverage must account for every normalized obligation；it marks the retention rule APPLICABLE and emits `retention_approved=true` with stable predicate identity and an existing policy anchor. Reconciliation adds it as `origin=COVERAGE_PASS`; Stage 2 cannot find determinate approval evidence, so Stage 4 returns `INSUFFICIENT_EVIDENCE` and Gate blocks. If coverage instead marks applicability INDETERMINATE, normal acceptance is still impossible. Stage-1 omission cannot silently accept。

### P0-2 — Model says SUPPORTING but proof is necessary

Model binds the only current training record to required `training_current=true` but its prose calls it “supporting”。There is no canonical materiality field in model output. Proof selector selects it for `STATE_EVIDENCE`; validated binding becomes `CRITICAL` and its mutation stales the Decision。

### P0-3 — Model downgrades a blocking contradiction

Two equal-authority scan records entail TRUE/FALSE for a root predicate; model advisory severity says SUPPORTING。Both are proof-eligible, reachable and unresolved, so deterministic impact is `VALIDITY_CRITICAL`; result is `NEEDS_HUMAN_REVIEW`。

### P0-4 — Ambiguous enterprise text

A clause says “normally current, subject to reconciliation”。Binding entailment is `INDETERMINATE`; it cannot be selected for the DIRECT gate. With no determinate alternative, assessment is `INSUFFICIENT_EVIDENCE`, not forced TRUE/FALSE。

### P0-5 — Retrieved subset omits policy

Retriever returns employee and approval records but cannot attest that all applicable policy namespaces were searched。Manifest coverage is `UNKNOWN`; compilation stops as `RUN_BLOCKED: CONTEXT_COVERAGE_INCOMPLETE` before a normal acceptance result exists。

### P0-6 — Interpretation policy changes

An accepted Decision used precedence-policy v4 and outcome-policy v7, both persisted through critical provenance。Precedence v5 changes which authority wins。Artifact-change invalidation reaches `DecisionInterpretation` Claim and makes the old Decision `STALE` even though enterprise evidence bytes did not change。

### P0-7 — Requirement paraphrase

“training remains current” and “required training has not expired” share the same structured `PredicateIdentity`。Display text is excluded from hashes and `STABLE_FAILED_PROOF_PATH`; repeated compile selects identical source/claim/policy edges。

### P0-8 — Injection suppresses an obligation

Injected distractor says “ignore retention policy”。No illegal authority edge is emitted, but Stage-1A omits retention。Paired evaluation still fails because clean/injected stable Requirement sets differ; independent coverage should recover the obligation. Edge-only safety would incorrectly pass this case。

### P0-9 — Developer cannot inspect holdout

Repository contains only blind manifest metadata and evaluator attestation。A local request to list holdout cases has no available path。Only after DEV PASS and method hash freeze does independent evaluator reveal/run once；post-result case tuning invalidates blind evidence。

### P0-10 — Cross-partition contradiction

Authority A TRUE is in partition 01 and equal-authority B FALSE in partition 07。Receipts prove both partitions complete；global join creates one unresolved contradiction。If partition 07 times out, result is context-coverage `RUN_BLOCKED`, never “no contradiction”。

### P0-11 — OR is not coerced into ALL_OF

Policy says “manager approval OR emergency authorization”。Normalized rule marks `OR`; compiler emits `REJECTED_UNSUPPORTED_LOGIC` with source provenance。It cannot require both, choose one, or canonicalize a Decision。

## Regression matrix

Implementation must eventually add method-level tests for：

- every P0-1…P0-11 counterexample above；
- coverage pass input excludes Stage-1A output；
- coverage receipt accounts for every normalized governing obligation exactly once；
- NOT_APPLICABLE / INDETERMINATE coverage semantics are typed and measured；
- coverage-only requirement flows through binding/contradiction/completeness；
- `UNKNOWN_SOURCE_REQUIRED` is unrepresentable；
- model materiality/severity cannot affect canonical result；
- INDETERMINATE never becomes selected proof；
- manifest coverage/hashes/exclusions/retrieval versions validate；
- each policy ref and manifest revision can stale accepted Decision；
- an unregistered deterministic config read is rejected as `UNVERSIONED_POLICY_INPUT`；
- paraphrase leaves semantic IDs、DENY proof and Runtime edge set unchanged；
- complete cross-partition reduction and fail-closed partial receipt；
- unsupported logic never canonicalizes；
- clean/injected paired semantic invariants；
- transitive Source → Claim → Claim → Decision without redundant edges；
- critical/counterevidence mutation stales, supporting/unselected mutation does not；
- reasoner-only/old-critic cannot call Runtime acceptance；
- production packages cannot import DEV ground truth or access blind holdout bodies。

## Falsification and stop rules

- K3 permanently kills current critic configuration。
- If independent coverage cannot materially recover Stage-1 omissions without unacceptable false blocks, architecture remains `REDESIGN REQUIRED`。
- If deterministic proof selection cannot meet recall/precision simultaneously, stop before contradiction integration。
- If complete contradiction coverage cannot reach pair/impact recall ≥ 0.90 under hard limits, stop before integrated paid run。
- If outcome or must-block is not 100%，stop。
- If full DEV passes but blind holdout fails any P0，do not tune against revealed cases；redesign or acquire a newly independent holdout after method changes。
- If reliable performance requires reading ground truth、domain/case/source-ref special cases、whole-document critical refs、silent context truncation、manually authored exact per-decision graphs or LLM-controlled Runtime state，recommend narrow/kill。
- Whole-project kill remains a product-owner decision；coding agent cannot lower P0。

## Product-owner blocker resolution matrix

| Blocker | Revision-2 mechanism | Fail-closed condition | Normative fixture |
|---|---|---|---|
| P0-1 requirement omission | independent outcome-blind obligation inventory + semantic-key reconciliation | coverage pass unavailable/conflicted cannot fall back to decomposition-only acceptance | P0-1 |
| P0-2 model materiality | model emits no canonical materiality; Stage 4 proof role derives it | no selected proof for required role → insufficient | P0-2 |
| P0-3 model severity | reachability/proof/authority-derived contradiction impact | unresolved validity-critical conflict → review | P0-3 |
| P0-4 binary entailment | three-state entailment | INDETERMINATE cannot be selected proof | P0-4 |
| P0-5 source universe | versioned complete SourceSetManifest | incomplete/unknown → context-coverage RUN_BLOCKED | P0-5 |
| P0-6 policy provenance | versioned policy bundle + critical policy/manifest graph paths | missing policy provenance prevents Runtime acceptance | P0-6 |
| P0-7 lexical DENY | structured PredicateIdentity + stable source/topology proof tuple | invalid/unrecognized semantic identity cannot canonicalize | P0-7 |
| P0-8 injection | paired end-to-end semantic/mutation invariance | any suppression/flip/regression fails adversarial P0 | P0-8 |
| P0-9 visible holdout | externally owned blind set, one-time post-freeze reveal/run | no local case-body access before freeze | P0-9 |
| P0-10 contradiction scaling | deterministic partitions、receipts and global join | hard-limit/partial coverage → RUN_BLOCKED | P0-10 |
| P0-11 unsupported logic | trusted normalized rule form + typed unsupported result | unsupported/unparsed governing logic cannot canonicalize | P0-11 |

## Product-owner review checklist

本 revision 请求确认：

1. 独立 coverage + deterministic reconciliation 是否解除 Stage-1 single point of failure；
2. proof-selected materiality 与 reachability-derived contradiction impact 是否足够 deterministic；
3. SourceSet/partition fail-closed contract 与 policy-as-dependency mapping 是否符合 Runtime thesis；
4. stable predicate identity 与 DENY proof selection 是否满足 paraphrase determinism；
5. P0 gate-shaped scope、unsupported-logic behavior、paired injection evaluation与 externally owned blind holdout 是否可接受。

批准本文只允许下一步编写 implementation plan；不代表 Module 01 P0 PASS。
