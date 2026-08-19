# Semantic Dependency Compiler Phase B–G 实施计划

> 执行要求：连续完成所有任务；每个行为先写会因缺少该行为而失败的测试，观察 RED，再写最小实现到 GREEN。不要向用户请求阶段确认。

**目标：** 从已完成的 Phase A 出发，实现、评估并以可运行产品交付 Module 01 Phase B–G，最后整体代码审查、合并 `main` 并推送。

**架构：** 新的 `app/compiler` 是 probabilistic reasoning 与 deterministic runtime 的隔离层。编译工件和运行时接受分事务；Gemini/ADK 只提议 typed draft/critic findings，规范 identity、validation、disposition、hash 和 runtime state 全部由确定性代码控制。

**技术栈：** Python 3.11+、Pydantic 2、FastAPI、Google ADK 2.x、Gemini 3.5+、SQLite、Firestore、Pub/Sub、React/TypeScript/Vite、pytest/Vitest/Playwright。

---

## Task 1：Phase B — IR 与无副作用编译骨架

**文件：**

- 新建 `backend/app/compiler/models.py`
- 新建 `backend/app/compiler/service.py`
- 新建 `backend/app/compiler/__init__.py`
- 新建 `backend/tests/compiler/test_ir.py`
- 新建 `backend/tests/compiler/test_compiler_pipeline.py`

**步骤：**

1. 先写 schema tests：合法 multi-claim draft、所有 enum、重复 local id、越界 confidence、空 statement、blocking question、extra fields、model metadata。
2. 运行目标 tests，确认因模块/行为不存在而 RED。
3. 实现 `DecisionDraft`、`ClaimDraft`、`DependencyRef`、`UnresolvedQuestion`、`ModelMetadata`、finding/contradiction/canonical/result types 和固定 disposition。
4. 写 pipeline test，证明阶段按 schema → validation → critic → contradiction → canonicalization 调用，并证明 compile 不触碰 runtime port。
5. 实现小型 stage protocols 和 `CompilerService`，跑 Phase B tests 到 GREEN。
6. 跑全部 backend tests，提交 `feat: add semantic compiler IR and pipeline`。

## Task 2：Phase C1 — V1–V4 schema/ref/scope/temporal validator

**文件：**

- 新建 `backend/app/compiler/context.py`
- 新建 `backend/app/compiler/validation.py`
- 新建 `backend/tests/compiler/test_draft_validation.py`
- 修改 `backend/app/sources/registry.py`（只在 protocol 缺失必要只读元数据时）

**步骤：**

1. 写表驱动 tests：unknown ref、非 canonical shorthand、错误 representation、snapshot stale、historical disallowed、owner scope unauthorized、合法 fully-qualified ref。
2. 观察 RED。
3. 实现 `CompilationContext`、固定 finding code/severity 和 V1–V4；所有 ref 都通过 `SourceRegistry.resolve`，allowlist 是 request-scoped 交集。
4. 验证 fatal finding 与 disposition 映射稳定，绝不 fuzzy repair。
5. 跑 compiler tests 和全部 backend tests到 GREEN。

## Task 3：Phase C2 — V5–V7、规范化和 hash

**文件：**

- 修改 `backend/app/compiler/validation.py`
- 新建 `backend/app/compiler/canonicalization.py`
- 新建 `backend/tests/compiler/test_relation_and_materiality_rules.py`
- 新建 `backend/tests/compiler/test_canonicalization.py`

**步骤：**

1. 写 tests：只有 policy/rule-like source 可 `GOVERNED_BY`；raw text 不可 `AUTHORIZES`；derived claim ref 必须存在且无禁止 cycle；critical FACT/RULE 必须有支持；高风险 approval 必须有 critical path。
2. 观察 RED 后实现 V5–V7。
3. 写 canonicalization tests：重复边坍缩、输入顺序无关、idempotent、stable canonical ids、stable hash、source hash/版本/compiler policy 改变会改变 hash。
4. 观察 RED 后实现规范序列化、stable sort/dedupe、canonical claim/edge/decision candidate 和 hash。
5. 增加 100-node proposal 性能 test（确定性部分 <100ms，保留合理本机容差与明确计时范围）。
6. 跑 Phase C 与全量 backend tests，提交 `feat: validate and canonicalize decision dependencies`。

## Task 4：Phase D1 — 有界只读 source tools

**文件：**

- 新建 `backend/app/compiler/tools.py`
- 新建 `backend/tests/compiler/test_source_tools.py`

**步骤：**

1. 写真实 in-memory registry tests：catalog search、exact fragment、structured field、current revisions、decision context、scope filtering、prompt-injected text 作为 data 返回。
2. 观察 RED。
3. 实现纯只读 tool facade，返回 opaque fully-qualified refs 和最小 metadata；不得暴露写入口。
4. 跑 tests 到 GREEN。

## Task 5：Phase D2 — provider-neutral reasoner、OpenAI 预算门与 ADK/Gemini executor

**文件：**

- 新建 `backend/app/compiler/prompts.py`
- 新建 `backend/app/compiler/reasoner.py`
- 新建 `backend/app/compiler/budget.py`
- 新建 `backend/tests/compiler/test_gemini_reasoner.py`
- 新建 `backend/tests/compiler/test_openai_reasoner.py`
- 新建 `backend/tests/compiler/test_model_budget.py`
- 新建 `backend/tests/live/test_live_openai_compiler.py`
- 新建 `backend/tests/live/test_live_gemini_compiler.py`
- 修改 `backend/pyproject.toml`（固定兼容版本范围和 live marker）

**步骤：**

1. 写 fake external transport contract tests：Pydantic structured output、工具返回 ref、schema 错误反馈后只重试一次、第二次失败、model metadata、prompt version、无隐藏 CoT 字段。
2. 观察 RED。
3. 实现 provider-neutral reasoner/critic contract；OpenAI Responses API 和 ADK/Gemini 共享同一 typed output，不共享 provider-specific transport。
4. 实现并发安全、持久化的 OpenAI budget ledger：累计硬上限 10 美元；调用前 reserve，调用后按 usage settle；余额不足在网络前拒绝；定价和版本进入审计。
5. 先接 OpenAI structured outputs 做真实验证，默认成本敏感模型由环境显式配置；其证据标为 `live_openai`，不覆盖 Gemini P0。
6. 基于已安装 ADK 2.x 官方 API 实现 reasoner/critic agents；模型默认 `gemini-3.5-flash` 或环境覆盖且必须满足 3.5+ allowlist；temperature/config 明确记录。
7. 对模型/网络边界做 dependency injection；unit tests 只替代最外层外部调用，不断言 mock 自身。
8. 添加两套 credential-gated live tests，缺凭据时 SKIP 且明确不能转化为 PASS；覆盖 multi-source、missing evidence、contradiction、prompt injection。
9. 运行 fake contract 和全量 tests，提交 `feat: integrate bounded model dependency reasoning`。

## Task 6：Phase E — 完整性、矛盾和 authority precedence

**文件：**

- 新建 `backend/app/compiler/review.py`
- 新建 `backend/app/compiler/policy.py`
- 新建 `backend/tests/compiler/test_completeness_review.py`
- 新建 `backend/tests/compiler/test_contradiction_review.py`
- 修改 `backend/app/compiler/service.py`

**步骤：**

1. 写 omission tests：CRITICAL 候选 ref 阻断、SUPPORTING warning、UNKNOWN_SOURCE_REQUIRED 阻断、critic fabricated/unauthorized ref 被确定性拒绝、irrelevant dependency finding。
2. 观察 RED 后实现 critic schema 的确定性验证和 disposition。
3. 写 contradiction tests：newer current policy > obsolete、signed approval > draft、canonical record > cache、mission override 仅显式配置生效、同 rank material conflict → review、权威直接否定 high-risk approval → reject。
4. 观察 RED 后实现 domain-configured precedence 和 first-class contradiction findings。
5. 用完整 CompilerService integration tests 验证固定顺序和结果工件。
6. 跑 Phase E 与全量 backend tests，提交 `feat: gate completeness and contradictions`。

## Task 7：Phase F1 — 120-case 真值 corpus

**文件：**

- 新建 `bench/dependency/schema.json`
- 新建 `bench/dependency/cases/vendor-onboarding/*.json`（40）
- 新建 `bench/dependency/cases/production-release/*.json`（40）
- 新建 `bench/dependency/cases/privileged-access/*.json`（40）
- 新建 `backend/app/compiler/benchmark/corpus.py`
- 新建 `backend/tests/compiler/benchmark/test_corpus.py`

**步骤：**

1. 先写 corpus validation tests：恰好/至少 120、每域 40、ID 唯一、ref 可解析、真值 source 存在、每例 mutation、五类 adversarial 各 >=10、30-case variance subset。
2. 观察 RED。
3. 定义 case schema 并版本化提交 120 个具名、可读、带 source fragment 内容和 ground truth 的案例；不在测试时生成真值。
4. 实现 corpus loader/validator，跑 tests 到 GREEN。

## Task 8：Phase F2 — runner、三基线、指标和报告

**文件：**

- 新建 `backend/app/compiler/benchmark/metrics.py`
- 新建 `backend/app/compiler/benchmark/runner.py`
- 新建 `backend/app/compiler/benchmark/report.py`
- 新建 `backend/app/compiler/benchmark/cli.py`
- 新建 `backend/tests/compiler/benchmark/test_metrics.py`
- 新建 `backend/tests/compiler/benchmark/test_runner.py`
- 新建 `docs/reports/module-01-dependency-compiler.md`

**步骤：**

1. 写手算 literal metrics tests：critical recall/precision、unsupported refs、contradiction recall、stale escape、unnecessary invalidation、domain floors、determinism。
2. 观察 RED 后实现纯指标函数。
3. 写 runner tests：document-level baseline、single-pass、full pipeline；live/fake evidence 分栏；3x30 variance；模型/配置/prompt 记录；失败指标让 gate 非零退出。
4. 观察 RED 后实现 runner、JSON report 和 Markdown summary。
5. 运行 deterministic corpus，保存实际报告；目标未达标则迭代 prompt/critic/compiler，但不改真值迎合实现。
6. 先在 10 美元累计上限内运行 live OpenAI corpus/adversarial/variance，保存实际 usage/cost；再在有凭据时运行 live Gemini 全 corpus + adversarial + variance。二者证据分开，无 Gemini 凭据时对应 P0 保持 BLOCKED。
7. 提交 `feat: add continuum dependency benchmark`。

## Task 9：Phase G1 — 编译持久化、API 和 outbox

**文件：**

- 新建 `backend/app/compiler/repository.py`
- 新建 `backend/app/compiler/repository_memory.py`
- 新建 `backend/app/compiler/repository_sqlite.py`
- 新建 `backend/app/compiler/repository_firestore.py`
- 新建 `backend/app/api/compiler_routes.py`
- 新建 `backend/tests/compiler/test_compiler_repository_contract.py`
- 新建 `backend/tests/compiler/test_compiler_api.py`
- 修改 `backend/app/main.py`

**步骤：**

1. 写 repository contract tests：request/draft/result 不可变、状态顺序、duplicate/idempotency、查询聚合、outbox event 类型。
2. 观察 RED，先实现 memory，再让 SQLite/Firestore adapter 通过同一 contract（Firestore emulator/fake client）。
3. 写 API tests 覆盖 proposed 5 endpoints、错误状态、compile 可重放、human route 不暴露 runtime accept capability。
4. 观察 RED 后实现 router/composition 和 structured error mapping。
5. 跑 repository/API/全量 tests。

## Task 10：Phase G2 — runtime acceptance 与并发审计

**文件：**

- 新建 `backend/app/compiler/acceptance.py`
- 修改 `backend/app/runtime/entities.py`
- 修改 `backend/app/repository/runtime_protocol.py`
- 修改 memory/SQLite/Firestore runtime repositories
- 修改 `backend/app/api/compiler_routes.py`
- 新建 `backend/tests/compiler/test_runtime_acceptance.py`
- 新建 `backend/tests/compiler/test_runtime_acceptance_concurrency.py`

**步骤：**

1. 写 integration tests：ACCEPTED 转 canonical Decision/claims/edges；非 accepted 拒绝；expected revision mismatch；world snapshot mismatch；接受幂等；并发只一个成功；audit 链接 compilation id/hash；编译失败零 runtime mutation。
2. 观察 RED。
3. 实现稳定 runtime ID translation 和 repository CAS；扩展持久化 model 时保持旧 demo/API 兼容。
4. 对 Memory、SQLite、Firestore contract 运行相同 acceptance behavior。
5. 跑全量 backend tests，提交 `feat: accept compiled decisions into runtime`。

## Task 11：产品面 — Compiler Lab

**前置：** 读取 `~/ai-memory/ui_style_rules.md` 和 `frontend-design` skill 后才改 UI。

**文件：**

- 修改 `frontend/src/types.ts`
- 修改 `frontend/src/api.ts`
- 修改 `frontend/src/App.tsx`
- 新建 `frontend/src/components/CompilerLab.tsx`
- 修改 `frontend/src/styles.css`
- 新建/修改 Vitest tests
- 新建 `frontend/e2e/compiler-lab.spec.ts`
- 增加本地 demo seed API/fixture（独立于 compiler logic）

**步骤：**

1. 先写 UI behavior tests：打开 Compiler Lab、创建/编译样例、展示 exact refs/claims/findings/hash、接受按钮只在 accepted + runtime-authorized demo flow 可用、execution/evidence mode 明示。
2. 观察 RED 后实现最小 UI 和 API types。
3. 用真实后端跑 Playwright happy path、invalid ref、omission/contradiction、stale accept path。
4. 检查 320/768/1440 宽度、keyboard、focus、contrast、loading/error/retry。
5. 跑 Vitest/Vite build/Playwright，提交 `feat: deliver semantic compiler lab`。

## Task 12：Cloud/运行说明和交付报告

**文件：**

- 修改 `.env.example`
- 修改 `README.md`
- 修改部署配置/脚本（如实际 composition 需要）
- 完成 `docs/reports/module-01-dependency-compiler.md`
- 更新 Module 01 acceptance matrix 的证据状态（只按实际证据）

**步骤：**

1. 验证本地 SQLite 一条命令启动、前端静态 bundle、Cloud Firestore/PubSub composition、Gemini 3.5+ mode 配置。
2. 报告实际模型、配置、corpus、指标、adversarial、测试命令、P1、偏差和明确 GO/REDESIGN/BLOCKED。
3. 不把 credential-gated skip 写成 pass。

## Task 13：整体 code review、修复、完成分支

**步骤：**

1. 使用 `requesting-code-review` 做独立全 diff 审查，覆盖 spec compliance、architecture、security、data race、Cloud composition、benchmark integrity、UI/API。
2. 对每条反馈使用 `receiving-code-review` 验证后 TDD 修复；重复审查直到无 Critical/Important。
3. 使用 `verification-before-completion` 运行：backend 全量 + coverage、live tests、benchmark gate、frontend tests/build、Playwright、git diff/status、秘密扫描。
4. 使用 `finishing-a-development-branch`；按用户既定要求把开发分支本地合回 `main`，保留未提交 `AGENTS.md`，推送 `origin/main`。
5. 最终以产品交付：运行方式、入口、真实证据、指标、架构、限制、commit 和远程状态；随后才将 goal 标为 complete。
