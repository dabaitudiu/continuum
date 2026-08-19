# 15 — Replacement Architecture: Requirement-Centred Compiler

## 文档状态

- Product owner 决策：**Option B 已批准**。
- 设计状态：**FOR REVIEW — 尚未实现**。
- 当前 vague critic：**已被架构决策否决**，不得作为最终 pipeline 保留。
- Option A（reasoner-only）：只保留为 ablation baseline，不是候选生产架构。
- Option C：不执行。
- 本文批准后才可编写 implementation plan；本文批准前不得修改 compiler 实现、生成 holdout case 或调用 live model。

## 决策依据

Experiment 1 已足以触发 K3：

- critic 只在 30 个 audited cases 中执行了 8 次；
- 新增的 5 次 block 全部是 false positive；
- 4 次虚构 `UNKNOWN_SOURCE_REQUIRED`；
- 1 次忽略已有的 transitive Claim → Claim / Decision requires Claim provenance；
- contradiction 与 omission cases 经常在 critic 之前被 validator 提前终止；
- critic 恢复 0 个 omission、发现 0 个 contradiction，却降低 precision、must-block compliance 与 acceptance coverage。

因此，问题不应被描述为“需要继续调 critic prompt”。旧架构同时混合了 requirement discovery、evidence checking、contradiction detection、completeness、severity 和 disposition，并且 pipeline 允许语义问题阻止对应语义 stage 执行。Option B 用显式 typed stages 取代该结构。

## 架构不变量

1. `Requirement` 是可审计的 semantic proposition，不是 source ref 的包装。
2. source identity、scope、temporal validity、authority class、precedence、canonicalization 和 final disposition 由 deterministic code 控制。
3. model 只能生成 immutable proposal；任何 model output 都不能直接写 canonical graph、Mission、Decision status、world snapshot 或 side effect state。
4. `CRITICAL` 表示反事实 materiality：该 source 的相关内容改变时，可能改变 requirement 或 decision validity。
5. 阅读过、相关或有解释价值，不足以成为 `CRITICAL`。
6. completeness 是 deterministic stage，只评估 Stage 1 已显式声明的 requirements；它不能发明 requirement，也不能输出占位 source ref。
7. contradiction detection 是独立 typed semantic pass，不是 completeness 的副作用。
8. structural failure 可以提前终止；semantic incompleteness、contradiction、uncertainty 和 outcome mismatch 必须等相关 semantic passes 执行后，才由 final gate 处置。
9. canonical support 按 graph reachability 计算；不得要求每个 derived Claim 或 Decision 再重复添加 direct source edge。
10. Module 02、full 120-case paid benchmark 和 live Gemini acceptance 均不在本设计阶段执行。

## Replacement pipeline

```mermaid
flowchart TD
    A[DecisionRequest + bounded SourceRegistry snapshot] --> B[0. Context Assembly]
    B --> C[1. Requirement Decomposition]
    C --> C1[Deterministic requirement structure validation]
    C1 -->|structural error| X[Terminal structural disposition]
    C1 --> D[2. Evidence Binding]
    D --> D1[Deterministic ref / scope / temporal / type validation]
    D1 -->|structural error| X
    D1 --> E[3. Independent Contradiction Pass]
    E --> E1[Deterministic candidate validation + precedence]
    E1 -->|structural error| X
    E1 --> F[4. Deterministic Requirement Completeness]
    F --> F1[Reachability + assessment computation]
    F1 -->|internal invariant failure| Y[RUN_FAILED]
    F1 --> G[5. Deterministic Acceptance Gate]
    G -->|ACCEPTED| H[Deterministic Canonicalizer]
    G -->|REJECT / REVIEW| I[Immutable non-accepted CompilationResult]
    H --> J[Immutable accepted CompilationResult]
    J --> K[RuntimeAcceptanceService]
    K --> L[Canonical Runtime graph mutation]
```

Stage 3 和 Stage 4 无论发现何种 semantic condition 都运行到底。比如 evidence 不足时，Stage 3 仍需检查已知 authorities 是否互相矛盾；发现 unresolved contradiction 后，Stage 4 仍需给每个 explicit requirement 生成 completeness assessment。只有 malformed/unauthorized/stale/illegal typed input 等 structural errors 可以提前结束。

## Compiler execution state

```mermaid
stateDiagram-v2
    [*] --> RECEIVED
    RECEIVED --> CONTEXT_READY
    CONTEXT_READY --> REQUIREMENTS_VALIDATED
    REQUIREMENTS_VALIDATED --> BINDINGS_VALIDATED
    BINDINGS_VALIDATED --> CONTRADICTIONS_VALIDATED
    CONTRADICTIONS_VALIDATED --> COMPLETENESS_COMPUTED
    COMPLETENESS_COMPUTED --> GATE_EVALUATED
    GATE_EVALUATED --> CANONICALIZED: ACCEPTED
    GATE_EVALUATED --> COMPLETED_NOT_ACCEPTED: REJECT / REVIEW
    CANONICALIZED --> COMPLETED_ACCEPTED

    RECEIVED --> RUN_BLOCKED: context auth / budget
    CONTEXT_READY --> RUN_BLOCKED: Stage 1 provider / budget
    REQUIREMENTS_VALIDATED --> RUN_BLOCKED: Stage 2 provider / budget
    BINDINGS_VALIDATED --> RUN_BLOCKED: Stage 3 provider / budget
    CONTEXT_READY --> TERMINAL_STRUCTURAL_ERROR
    REQUIREMENTS_VALIDATED --> TERMINAL_STRUCTURAL_ERROR
    BINDINGS_VALIDATED --> TERMINAL_STRUCTURAL_ERROR
    RECEIVED --> RUN_FAILED: internal / persistence invariant
    CONTEXT_READY --> RUN_FAILED: internal / persistence invariant
    REQUIREMENTS_VALIDATED --> RUN_FAILED: internal / persistence invariant
    BINDINGS_VALIDATED --> RUN_FAILED: internal / persistence invariant
    CONTRADICTIONS_VALIDATED --> RUN_FAILED: internal / persistence invariant
    COMPLETENESS_COMPUTED --> RUN_FAILED: internal / persistence invariant
```

`RUN_BLOCKED` 是 execution status，不是 semantic compilation disposition。Credential、transport、budget 或 provider outage 不能伪装成 `REJECTED_*`，更不能产生 canonical output。

## Typed contracts

以下四个类型是 immutable analysis IR。它们不是 Runtime entity，也没有 canonical mutation capability。所有 local IDs、source refs 和 cross-links 都必须经 deterministic validation 后才能进入下一 stage。

Stage 1 的 transport envelope 是：

```text
DecisionAnalysisProposal
  request_id: string
  decision_type: string
  proposed_outcome: one trusted request outcome option
  requirements: list[Requirement]
  rationale_summary: string
```

`proposed_outcome` 仍是 model proposal，不是 canonical state。Trusted request只提供完整 outcome vocabulary及其 `APPROVE | DENY | REVIEW` class mapping，不提供 case expected outcome。Deterministic gate根据 RequirementAssessments独立计算 expected class并校验 proposal。

### 1. `Requirement`

```text
Requirement
  requirement_local_id: string
  proposition: string
  kind: FACT | RULE | AUTHORIZATION | EVIDENCE_PRESENCE | NEGATIVE_CONSTRAINT
  expected_truth: TRUE | FALSE
  proof_mode: DIRECT | DERIVED_ALL
  depends_on_requirement_ids: list[string]
  rationale_summary: string
```

约束：

- `proposition` 必须是独立可判定的语义命题，例如“requester 已完成当前安全培训”，不能是 `access-policy#training`。
- Stage 1 schema **禁止任何 source-ref 字段**。
- P0 中每个 Requirement 都是 APPROVE validity 的必要前提，不存在 `SUPPORTING Requirement`。解释性信息不进入 Requirement set；`CRITICAL | SUPPORTING` 只用于 EvidenceBinding。
- `expected_truth` 定义该 proposition 对 APPROVE 必须取的真值。例如 proposition“requester is suspended”配 `FALSE`；assessment 证明其为 false 时 Requirement 才是 `SATISFIED`。
- `proof_mode=DIRECT` 要求 `depends_on_requirement_ids` 为空，并且其 proposition可由一个 source fragment独立判定真值。若必须联合多个事实/规则才能成立，Stage 1 必须拆成多个 DIRECT prerequisites，再用 DERIVED_ALL 汇合。
- `proof_mode=DERIVED_ALL` 要求至少一个 dependency，且仅当所有 prerequisite Requirements 都 `SATISFIED` 时才 `SATISFIED`；它不要求 redundant direct CRITICAL binding。CRITICAL binding 只能目标为 `DIRECT` Requirement，避免 direct 与 derived proof互相冲突。
- `depends_on_requirement_ids` 形成 conjunction-only DAG；self-edge、unknown ID 和 cycle 是 structural error。P0 不支持模型自定义 boolean expression 或 `DERIVED_ANY`；alternative evidence 应绑定到同一个 DIRECT Requirement。
- 空 requirement set 是 semantic gap，不是 schema shortcut；pipeline 继续到 Stage 3/4，最终由 gate 拒绝。
- Stage 1 如果漏掉真实 requirement，Stage 4 不得“补猜”。该风险由独立 requirement ground truth 和 benchmark recall 暴露，而不是由另一个 open-ended critic 掩盖。

### 2. `EvidenceBinding`

```text
EvidenceBinding
  binding_local_id: string
  requirement_local_id: string
  source_ref: canonical SourceRef
  semantic_role: EVIDENCE | GOVERNING_AUTHORITY | SATISFACTION_RECORD
  entailed_truth: TRUE | FALSE
  materiality: CRITICAL | SUPPORTING
  validity_impact: MAY_CHANGE_VALIDITY | EXPLANATION_ONLY
  counterfactual_summary: string
```

约束：

- `source_ref` 必须来自 request-scoped `SourceRegistry` inventory，并在当前 world snapshot 下通过 identity、scope、temporal 和 authority validation。
- `entailed_truth` 表示该 fragment 对 Requirement proposition 本身支持 true 还是 false，不是对 proposed outcome 的投票。deterministic assessment 将它与 Requirement `expected_truth` 比较：相等是支持 APPROVE 前提，相反是 counterevidence。
- `CRITICAL` 当且仅当 `validity_impact=MAY_CHANGE_VALIDITY`；`SUPPORTING` 当且仅当 `EXPLANATION_ONLY`。deterministic code 强制字段一致性，benchmark 验证语义是否正确。
- `counterfactual_summary` 必须回答“这个 fragment 的相关内容变化时，哪个 requirement/outcome 可能改变”；它是 concise audit rationale，不是 chain-of-thought。
- `CONTEXTUAL` 不进入 binding contract。纯上下文仍可记录为 model-read telemetry，但不能成为 validity edge。
- Binding stage 追求 minimal sufficient set。相关但对 validity 无反事实影响的 evidence 必须是 `SUPPORTING` 或省略。
- Stage 2 不能创建 canonical edge，只能提出 binding。
- CRITICAL binding 只能指向 `proof_mode=DIRECT` Requirement；DERIVED_ALL 的 validity 来自 prerequisite Claim closure。SUPPORTING binding 可以附着于任一 Requirement用于解释，但不参与 gate 或 stale propagation。
- 同一 DIRECT Requirement若有多个 precedence 后同向 CRITICAL candidates，deterministic completeness按 `authority_rank DESC, canonical_source_ref ASC` 选择一个 `proof_binding_id`；其他 candidates留在 compiler analysis record，不进入 Runtime critical graph。相反真值同时存活则是 `CONTRADICTED`，不能用排序掩盖。

### 3. `Contradiction`

```text
ContradictionCandidate                     # model proposal
  contradiction_local_id: string
  requirement_local_id: string
  lhs_ref: canonical SourceRef
  rhs_ref: canonical SourceRef
  lhs_entailed_truth: TRUE | FALSE
  rhs_entailed_truth: TRUE | FALSE
  proposition: string
  contradiction_type:
    DIRECT_NEGATION | VALUE_MISMATCH | SCOPE_CONFLICT |
    TEMPORAL_CONFLICT | AUTHORITY_CONFLICT
  severity: CRITICAL | SUPPORTING
  model_resolvable_by_precedence: boolean
  model_recommended_disposition: BLOCK | HUMAN_REVIEW | IGNORE_AFTER_PRECEDENCE

Contradiction                              # deterministic validated record
  candidate: ContradictionCandidate
  lhs_binding_id: string | null
  rhs_binding_id: string | null
  deterministic_resolution: LHS_PRECEDES | RHS_PRECEDES | UNRESOLVED
  precedence_rule_id: string | null
  validation_finding_codes: list[string]
```

Ownership：

- model 只输出 `ContradictionCandidate` 的 ref pair、entailed truth、semantic proposition、type、severity 和非权威 recommendation；
- deterministic code 验证 refs、scope、temporal validity、source classes、authority rank 和 pair identity；
- validator 生成 `Contradiction` record；`lhs_entailed_truth` / `rhs_entailed_truth` 都相对于 Requirement proposition，若对应 binding存在则要求 truth 与 binding 完全一致，并把匹配 ID 写入 record；
- deterministic precedence policy 独立计算 `deterministic_resolution` 与 `precedence_rule_id`；model 的 `resolvable` 或 `recommended_disposition` 不能覆盖该结果；
- `lhs_binding_id` / `rhs_binding_id` 由 validator解析，可以为空，因为 dedicated pass 必须能发现尚未被 Evidence Binding 选中的 current/in-scope ref。

Stage 3 不拥有 binding promotion。若 precedence winner 没有与其 ref/truth/Requirement匹配的 validated CRITICAL EvidenceBinding，结果不能 ACCEPT；Completeness 将其视为 incomplete。Contradiction stage 不能通过“发现 ref”直接把它送进 canonical graph。

Stage 3 的输入是：explicit requirements、validated bindings、request-scoped bounded inventory 中**全部 current/in-scope candidate fragments**、authority metadata 和 current snapshot，而不是只看 Stage 2 选择的 refs。Semantic detector 自己判断哪些 candidates 与 Requirement 相关；它不能访问 benchmark contradiction labels。P0 不在 contradiction pass 前增加另一个未评估的 semantic retrieval filter。

### 4. `RequirementAssessment`

```text
RequirementAssessment
  requirement_local_id: string
  status: SATISFIED | UNSATISFIED | CONTRADICTED | INSUFFICIENT_EVIDENCE
  critical_binding_ids: list[string]
  supporting_binding_ids: list[string]
  proof_binding_id: string | null
  contradiction_ids: list[string]
  support_paths: list[list[string]]
  blocking_requirement_ids: list[string]
  missing_evidence_proposition: string | null
  finding_codes: list[string]
  assessment_summary: string
```

约束：

- `RequirementAssessment` 完全由 deterministic completeness stage生成；model 没有该类型的写权限。
- 每个 explicit `Requirement` 必须且只能有一个 assessment。
- 对 `DIRECT`：precedence 后的 CRITICAL bindings 只支持 `expected_truth` → `SATISFIED`；只支持相反真值 → `UNSATISFIED`；两边仍成立 → `CONTRADICTED`；无充分 CRITICAL binding → `INSUFFICIENT_EVIDENCE`。SATISFIED/UNSATISFIED 按固定 authority/ref排序得到唯一 `proof_binding_id`。
- 对 `DERIVED_ALL` 按优先级：任一 `CONTRADICTED` → `CONTRADICTED`；否则任一 `UNSATISFIED` → `UNSATISFIED`；否则全部 `SATISFIED` → `SATISFIED`；否则 → `INSUFFICIENT_EVIDENCE`。这保证 unresolved material conflict不会被另一个已知 false prerequisite掩盖。
- `critical_binding_ids`、`supporting_binding_ids`、`proof_binding_id` 和 `contradiction_ids` 必须引用前序 validated objects；DERIVED_ALL 的 `proof_binding_id` 必须为空。
- 只有 unresolved `severity=CRITICAL` Contradiction 或相反真值的 CRITICAL binding collision能产生 `CONTRADICTED`；SUPPORTING contradiction保留为 finding，不改变 status或 disposition。
- `support_paths` 由 code计算为从 DIRECT Requirement 到当前 Requirement 的 ordered DAG paths；`blocking_requirement_ids` 精确列出导致 derived assessment不能满足的 prerequisites。
- `missing_evidence_proposition` 对缺证的 DIRECT Requirement只能 deterministic copy/format该 Requirement proposition。它**没有 source-ref 类型**，不得包含 `UNKNOWN_SOURCE_REQUIRED` 或任何 invented ref。
- `finding_codes` 和 `assessment_summary` 使用 deterministic templates；Completeness 不新增 binding、不改 materiality、不改 outcome。

## Canonical graph mapping 与 transitive semantics

新 analysis IR 不改变 Continuum 已有的 canonical reachability 语义：

```text
SourceFragment
    --SUPPORTED_BY / GOVERNED_BY[CRITICAL]-->
Claim(requirement assessment: SATISFIED or UNSATISFIED)
    --DERIVED_FROM / REQUIRES[CRITICAL]-->
Claim(derived requirement assessment)
    --REQUIRES[CRITICAL]-->
Decision
```

从存储边方向看是 `Source → Claim → Claim → Decision`；从 dependency 视角看是 `Decision requires Claim`。两种叙述指向同一个 reachability invariant。

规则：

1. 一个 `RequirementAssessment` canonicalize 为一个 auditable Claim，statement 同时记录 Requirement proposition、`expected_truth` 与 validated assessment status；DERIVED_ALL DAG canonicalize 为 prerequisite Claim → derived Claim edges。
2. Evidence Binding 只在 DIRECT evidence leaf 创建 SourceFragment → assessment Claim edge。无论 source 支持 expected truth（APPROVE）还是支持相反真值（DENY），accepted Decision 都通过 validity-bearing `SUPPORTED_BY` / `GOVERNED_BY` CRITICAL edge 依赖该 source。
3. completeness 用 validity-bearing `CRITICAL` edge closure 判断 support。
4. 只有 DAG root Requirement Claims（未被其他 Requirement作为 prerequisite 引用）连接到 Decision；derived requirement 已有有效 transitive path 时，不创建 redundant direct SourceFragment → derived Claim，也不把每个 intermediate Claim重复直连 Decision。
5. `SUPPORTING` edge 不参与 validity reachability，也不能触发 Runtime stale propagation。
6. `CONTRADICTED_BY` 不是当前 Runtime kernel 的 direct invalidation relation，不能作为 accepted DENY 的唯一 provenance edge。Unresolved contradiction 只产生 non-accepted compiler finding；resolved contradiction 只有在 winner 已有匹配 validated CRITICAL EvidenceBinding时，才把该 binding映射到 assessment Claim。
7. Stage 3 发现但被 deterministic precedence 解决的 source pair保存在 compiler findings 中；只有经 gate 接受并由 canonicalizer 明确映射的 binding 才进入 Runtime graph。

这直接修复旧 critic 在 `vendor-onboarding-009` 中忽略 `derived_from_claims` 和 Decision `REQUIRES` path、强制要求重复 direct edges 的错误。

## Stage ownership

| Stage | Model ownership | Deterministic ownership | 不拥有 |
|---|---|---|---|
| Context Assembly | 无 | bounded inventory、allowed refs、snapshot、authority metadata、trusted outcome semantics | semantic requirement discovery |
| Requirement Decomposition | 提出 APPROVE validity 所需的 atomic propositions、DIRECT/DERIVED_ALL proof mode 与 requirement DAG | schema、IDs、conjunction DAG、expected-truth vocabulary、size limits | source refs、canonical claims、disposition |
| Evidence Binding | 提出 requirement↔source semantic bindings、materiality、counterfactual rationale | ref identity、scope、time、source type、authority legality、field consistency | canonical edges、precedence、acceptance |
| Contradiction Pass | 提出 semantic conflict candidates | candidate integrity、authority metadata、precedence、resolution | completeness、final disposition、state mutation |
| Requirement Completeness | 无 | 按固定 truth table计算每个 assessment、graph closure、support paths、blocking IDs、deterministic findings | 新 requirement、新 source ref、新 binding、semantic invention、outcome rewrite |
| Acceptance Gate | 无 | trusted outcome class、all Requirement coverage、contradiction policy、disposition | semantic invention、model retry |
| Canonicalizer | 无 | stable IDs、edge mapping、hash、ordering、dedupe | semantic repair、Runtime commit |
| RuntimeAcceptanceService | 无 | immutable accepted-result check、mission revision、world snapshot、atomic Runtime mutation | compiler semantics、LLM execution |

## Terminal 与 non-terminal semantics

### 可提前终止的 structural errors

| Error class | 最早发现位置 | Result |
|---|---|---|
| invalid JSON/schema after one bounded repair | corresponding model stage | `REJECTED_SCHEMA` |
| duplicate/unknown local ID、illegal enum、requirement cycle | post-stage structure validator | `REJECTED_INVALID_STRUCTURE` |
| unknown/fabricated source ref | Evidence/Contradiction validator | `REJECTED_INVALID_REFERENCE` |
| unauthorized/cross-scope ref | Evidence/Contradiction validator | `REJECTED_INVALID_REFERENCE` |
| disallowed historical or stale authority | Evidence/Contradiction validator | `REJECTED_STALE_SOURCE` |
| illegal source relation/authority class | Evidence validator | `REJECTED_INVALID_STRUCTURE` |
| internal invariant/persistence failure | orchestrator | run `FAILED`; no semantic disposition |
| credential/transport/provider/budget unavailable | orchestrator | run `BLOCKED`; no semantic disposition |

每个 terminal result 必须记录精确 `executed_stages`；未执行的 stage 明确为 `SKIPPED_STRUCTURAL_TERMINATION`，不能被展示成“未发现问题”。

### 不得提前终止的 semantic conditions

| Condition | 旧行为问题 | 新行为 |
|---|---|---|
| explicit requirement 没有 critical binding | validator 可能立即 incomplete | 继续 contradiction + completeness；gate 决定 incomplete |
| requirement set 为空 | 容易被当成“无问题” | 继续 semantic passes；gate 产生 incomplete |
| blocking unresolved question | `BLOCKING_QUESTION_UNRESOLVED` 使 critic 跳过 | 表达为 `INSUFFICIENT_EVIDENCE` assessment；相关 semantic passes 全部执行 |
| high-risk proposal 暂无 support path | validator 立即 block | 继续全部 semantic passes；gate 检查最终 closure |
| conflicting authorities | 常被 incomplete 提前截断 | dedicated contradiction pass 必须执行并产出 typed finding |
| unresolved material contradiction | critic/reviewer 直接结束 | 继续 completeness；gate 产生 review/reject |
| proposed outcome 与 evidence 不一致 | reasoner 自行决定或漏检 | 继续 pipeline；gate 应用 trusted outcome semantics |
| model semantic uncertainty | vague unresolved question | assessment 为 `INSUFFICIENT_EVIDENCE`；gate deterministic 处置 |

## Deterministic Acceptance Gate

`DecisionRequest` 必须由 trusted caller 提供 `outcome_semantics`，将每个允许的 domain outcome 映射到 `APPROVE | DENY | REVIEW`。这不是 benchmark ground truth，也不暴露 case-specific allowed outcome。P0 中所有 Requirements 都描述 APPROVE validity；model 不能自行把 Requirement 分配给某个 outcome class。

Gate 按以下固定顺序执行：

1. 若 run 存在 structural terminal error，不进入 gate。
2. 验证 Requirement set 非空，且每个 Requirement 恰有一个 deterministic assessment；识别所有 DAG roots。
3. 计算 expected outcome class：root closure有 unresolved CRITICAL contradiction → `REVIEW`；否则全部 roots `SATISFIED` → `APPROVE`；否则任一 root `UNSATISFIED` → `DENY`；否则 → `REVIEW`。
4. resolved contradiction 的 winning authority必须有匹配的 validated CRITICAL binding并折入对应 RequirementAssessment；缺少 winner binding 立即产生 `REJECTED_INCOMPLETE_REQUIREMENTS`，绝不由 Stage 3 自动补边。
5. 若 expected class=`REVIEW` 且原因包含 unresolved CRITICAL contradiction，统一返回 `NEEDS_HUMAN_REVIEW`；即使 model错误提议 APPROVE/DENY，也不能 ACCEPT。
6. 若 expected class=`REVIEW` 且原因只有 insufficient evidence：model提议 REVIEW → `NEEDS_HUMAN_REVIEW`；model提议 APPROVE/DENY → `REJECTED_INCOMPLETE_REQUIREMENTS`。两者都不产生 canonical graph。
7. 若 expected class=`APPROVE`：所有 roots必须 `SATISFIED`并可追溯到 current、authorized、validity-bearing CRITICAL DIRECT source paths；proposal class不是 APPROVE → `REJECTED_OUTCOME_CONSTRAINT`。
8. 若 expected class=`DENY`：至少一个 root必须 `UNSATISFIED`且其 closure内有 current、authorized、validity-bearing CRITICAL counterevidence path；proposal class不是 DENY时，若直接原因是 precedence winner则 `REJECTED_CONTRADICTION`，否则 `REJECTED_OUTCOME_CONSTRAINT`。单纯缺证据不能伪装成 DENY。
9. 只有 expected class为 APPROVE/DENY且 proposal class完全匹配时才可 `ACCEPTED`。Gate 同时生成 deterministic `DecisionJustification`，canonicalizer只消费该 proof slice。

```text
DecisionJustification
  outcome_class: APPROVE | DENY
  selected_root_requirement_ids: list[string]
  selected_requirement_ids: list[string]
  selected_critical_binding_ids: list[string]
  selection_rule: ALL_APPROVAL_ROOTS | CANONICAL_FIRST_FAILED_ROOT_PATH
```

- APPROVE 的 minimal sufficient proof 是全部 satisfied root closures。
- DENY 的 conjunction false proof只需一个 failed root path；若有多个，按 normalized canonical requirement key（kind、proposition、expected truth、proof mode）排序，稳定选择第一个。不能按 benchmark case ID、domain 或 model local-ID顺序选择。
- `selected_critical_binding_ids` 只包含 selected DIRECT assessments 的唯一 `proof_binding_id`，不包含未选中的同向 alternatives。
- DENY 的其他 failed/satisfied roots仍保存在 compiler analysis record，但不进入 Runtime critical graph。这样 source 改变只会使实际选用的 denial rationale stale，而不会因未参与该 Decision justification 的 sibling变化造成过度 invalidation。
- selected path上的 counterevidence变化会使原 Decision rationale不再有效，即使重新计算后可能因另一失败 root继续 DENY；这正是 Semantic Resume 应触发 revalidation 的条件。
- REVIEW 没有 `DecisionJustification`，也没有 canonical graph。

Gate 是 deterministic 的，但它不会把 probabilistic semantic labels magically 变成 truth。Requirement decomposition、binding materiality 和 semantic contradiction quality仍必须由 DEV/HOLDOUT/live-provider benchmark falsify。

## Old critic migration/removal plan

### M0 — Freeze，不再演进

- 将现有 `reasoner-v2 + critic-v1` 行为、prompt、schema、raw evidence 和 corrected evaluator 固定为 `legacy-critic-v1`。
- 不再调 `critic-v1` prompt，不再修成“看起来像”新架构。
- 历史 reports 保持 immutable。

### M1 — 从 active architecture 移除

- 实现开始时，`ModelDependencyCritic` / `DeterministicReviewGate` 从 v2 orchestrator 和默认候选生产 wiring 中移除。
- legacy adapter 只能由 benchmark 的显式 `pipeline=old-critic` 选择，不能接受 Runtime traffic。
- v2 failure 不得 fallback 到 old critic。
- reasoner-only 同样只能由 benchmark 显式选择。

### M2 — Parallel v2 contract

- 新 typed contracts 和 stage outputs 使用独立 version namespace；不得把旧 `CriticProposal` 字段复用成 requirement/contradiction/completeness 类型。
- 在 v2 通过 integrated DEV subset 前，generic model-backed compiler 保持 not accepted for product claims；deterministic reference demo不计 model evidence。
- persisted result 显式记录 `pipeline_version`、Stage 1–3 的 prompt/schema/model metadata与 usage，以及所有 stage 的 execution status；Stage 4/5不得伪造 model metadata。

### M3 — Cutover

- 只有新架构通过 Experiment 5 progression gate 后，v2 才成为唯一可进入后续 full DEV evaluation 的 pipeline。
- old critic 的 product wiring、prompt export 和 API response field `critic_findings` 从 active surface 删除；必要的 legacy reader 留在 benchmark/report namespace，用于重放已有 evidence。
- 不保留 compatibility fallback。旧 report 中的 field 仍可由 versioned reader 解析。

### M4 — Final cleanup

- full DEV、locked holdout 和 live Gemini 全部 P0 PASS 后，删除非重放所需的旧 critic implementation/tests。
- 在此之前 Module 01 状态始终是 `NOT READY` 或 `REDESIGN REQUIRED`，不能称为 DONE。

## Benchmark integrity before implementation

### Frozen requirement annotation

现有 120 cases 的 refs/outcomes/mutations 不得修改。为评估 Stage 1，在写 v2 prompt/schema 前，由 method-blind annotation 单独生成 `requirement-ground-truth-v1`：

- 每个 case 只描述 APPROVE-validity semantic propositions、expected truth、proof mode 和 conjunction DAG；
- 不复制 model output，不改变现有 required/forbidden refs；
- annotation 与 corpus file hashes 一起 freeze；
- production code/prompts 不得 import 或读取 annotation；
- 后续只能修客观 annotation bug，并以新版本和审计说明追加，不能覆盖历史版本。

### Locked generalization set

在任何 v2 prompt/schema/logic 实现之前一次性生成并 commit：

- 60 cases：3 domains × 20；
- 每个 domain 对现有 10 个 semantic classes 各 2 cases；
- semantic categories 与 DEV 相同，但 scenario family、task wording、source wording、fragment arrangement、source order 和 distractor layout 明显不同；
- 独立目录与 schema；production package 不得依赖；
- manifest 记录每文件 SHA-256、按路径排序的 aggregate SHA-256、authoring tool hash、schema version 和 freeze commit；
- 生成后不得为任何 individual holdout case 调 prompt、logic、threshold 或 ground truth；
- DEV 未通过前不得运行 holdout live inference。

这一步是设计批准后的 implementation Step 0；本次 design review 不生成 case。

## Ablation plan

### 三个 primary arms

| Arm | 目的 | 架构地位 |
|---|---|---|
| A — reasoner-only | 当前单 pass 能力下限 | baseline only；不得进入 final Runtime architecture |
| B — old critic pipeline | 已触发 K3 的历史二 pass | frozen legacy baseline；不得继续调优 |
| C — new requirement-centred pipeline | Option B 候选 | 唯一可能进入后续 acceptance 的架构 |

A/B 使用 Experiment 1 的 immutable paired reasoner evidence重算，不新增 legacy calls。C 使用同一个 frozen 30-case stratified subset、相同 task/source context、provider/model/service tier/reasoning settings 和 metric implementation；因 schema 与 call topology 是实验变量，prompt version 与 call count显式不同。报告必须同时披露 quality、accepted coverage、calls、latency 和总成本。

### Stage experiments

所有 live experiment 运行前必须 commit 一份 preregistration：hypothesis、code/prompt/schema hashes、case selection rule、max calls、worst-case reserved cost、success/failure interpretation。无 preregistration 不调用模型。

1. **Experiment 2 — Requirement + Evidence Binding**

   只跑预先按 class 选定的 DEV precision subset；检验 requirement recall、critical precision、supporting/critical separation 和 transitive support。成功信号：critical recall ≥ 0.92、precision ≥ 0.82、unknown refs = 0，且不要求 redundant direct edges。
2. **Experiment 3 — Dedicated Contradiction**

   只跑 DEV contradiction class；检验 pair recall、critical severity recall、precedence 和 equal-authority block。成功信号：两项 contradiction recall ≥ 0.90、must-block = 100%，且每个 case 的 contradiction stage 均执行。
3. **Experiment 4 — Deterministic Outcome Gate**

   只跑预先冻结的 must-block/outcome subset；检验 `APPROVE/DENY/REVIEW` mapping。成功信号：outcome compliance = 100%、must-block compliance = 100%，semantic condition 不造成 stage skip。
4. **Experiment 5 — Integrated three-arm DEV subset**

   在 frozen 30 cases 上比较 A/B/C。只有 C 同时满足所有现行 P0 quality thresholds、unsupported canonical refs = 0、所有 expected-accept cases被接受、所有 must-block cases不被接受、accepted mutation direction全部正确，才允许 Experiment 6。

### 后续 gate（本次不运行）

- Experiment 6：只有 Experiment 5 PASS 后才跑 full 120 DEV。
- Experiment 7：只有 full DEV 全 P0 PASS 后才首次运行 locked holdout；DEV 和 HOLDOUT 分开报告。
- Experiment 8：只有 OpenAI DEV + HOLDOUT 证明 methodology 成立后，才运行 required live Gemini acceptance。
- 任一阶段 FAIL，先停下产出 evidence-backed analysis，不机械继续后续付费实验。

### 共同 metrics

- requirement proposition/proof-mode recall（C only；A/B明确记 `N/A`，不能伪记 0 或 100%）；
- EvidenceBinding proposal critical recall / precision；
- accepted `DecisionJustification` canonical critical recall / precision与 corpus coverage；
- CRITICAL↔SUPPORTING confusion matrix；
- contradiction recall / critical severity recall；
- outcome compliance / must-block compliance；
- accepted-case coverage 与 disposition confusion matrix；
- unsupported canonical refs；
- accepted-only stale escape / unnecessary invalidation，连同 denominator；
- compilation determinism；
- deterministic outcome-class / minimal-justification selection；
- stage execution coverage；
- calls、input/cache-write/cache-read/output tokens、latency、settled cost。

三臂 headline comparison只使用所有 arms均可定义的 dependency、contradiction、outcome、disposition、Runtime mutation、coverage与 cost metrics。C-only typed diagnostics单列，不混入 A/B aggregate。

不得再把 proposal-union recall、accepted canonical coverage 和 NOT_ACCEPTED mutation records混成同一指标。

## Regression requirements

实现必须新增 method-level fixtures，而不是 case-ID hacks：

- supporting ref 被错误提升为 CRITICAL → 保持 SUPPORTING 或省略；
- critical fragment 变化 → accepted Decision becomes STALE；
- DENY 所依赖的 CRITICAL counterevidence fragment变化 → accepted DENY Decision becomes STALE；
- DENY 未选入 minimal proof 的 sibling fragment变化 → Decision stays VALID；
- supporting/irrelevant fragment 变化 → Decision stays VALID；
- equal-authority contradiction → dedicated pass发现且不能 silently ACCEPT；
- v1 遗漏的 material dependency → Stage 1/2 形成 explicit Requirement + EvidenceBinding，并进入 accepted canonical graph；
- 真实 evidence 缺失 → assessment 为 insufficient，并在 gate block；
- existing Source → Claim → Claim → Decision path → completeness 接受，无 redundant direct edge；
- stale historical ref不能支持 accepted requirement；
- prompt injection 不能创建 authority edge；
- semantic incompleteness不能跳过 contradiction/completeness；
- reasoner-only / old critic / new architecture ablation routing准确；
- production compiler无法 import benchmark ground truth 或 holdout annotations。

## Falsification and stop rules

- K3 已经终止 current critic configuration；该结论不因 sunk cost 反转。
- 若 Experiment 2 不能同时达到 precision ≥ 0.82 和 recall ≥ 0.92，停止进入 contradiction integration，回报 `REDESIGN REQUIRED`。
- 若 Experiment 3 contradiction recall 或 critical severity recall低于 0.90，停止进入 integrated paid run，回报 `REDESIGN REQUIRED`。
- 若 Experiment 4 outcome 或 must-block不是 100%，停止 Experiment 5。
- 若 Experiment 5 未达到 progression gate，不运行 full 120。
- 若 full DEV PASS 但 locked holdout 任一 P0 metric FAIL，Module 01 为 `REDESIGN REQUIRED`；不得用 DEV 数字覆盖 generalization failure。
- 若要达标必须读取 ground truth、加入 domain/case/source-ref special case、把 refs 放宽到 whole-document 造成 K2，或让 model 直接决定 Runtime stale state，则推荐 narrow/kill，而不是继续调参。
- whole-project kill 仍由 product owner 决定；coding agent 只能依据 `13_ACCEPTANCE_MATRIX_AND_KILL_CRITERIA.md` 给出 `REDESIGN REQUIRED` 或 kill recommendation，不能自行降低 P0。

## Review checklist

Product owner 批准本设计时，应明确确认：

1. 四个 typed contracts 与 enum 是否足够稳定，可以进入 implementation plan；
2. `DENY` 与 `REVIEW` 的 deterministic outcome semantics 是否符合产品意图；
3. old critic 只保留 benchmark legacy reader、不保留 production fallback；
4. holdout 必须在 v2 实现前 freeze；
5. Experiment 5 前不跑 full 120，DEV PASS 前不打开 holdout。

设计批准不代表 Module 01 PASS。当前状态仍是 **REDESIGN REQUIRED**。
