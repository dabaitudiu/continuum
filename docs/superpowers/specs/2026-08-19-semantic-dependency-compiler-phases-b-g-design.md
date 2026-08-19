# Semantic Dependency Compiler Phase B–G 设计锁定

日期：2026-08-19

## 目的

本设计只负责把 Module 01 的既有权威规格落实到当前仓库，不重新定义产品语义。权威需求仍是 `docs/continuum_module_01_semantic_dependency_compiler/` 下的 00–14 文档；发生冲突时，以该目录和 `AGENTS.md` 的确定性运行时不变量为准。

## 边界

Phase A 已完成 `Artifact -> Revision -> ParsedRepresentation -> Fragment`、世界快照绑定和规范 `SourceRef`。Phase B–G 在其上新增：

1. 类型化 Decision/Claim/Dependency IR；
2. 固定顺序的确定性验证和规范化；
3. Google ADK + Gemini 3.5+ 的只读双阶段推理；
4. 完整性、矛盾和权威优先级门；
5. 120 个版本化真值案例及可复现指标；
6. 编译记录、API、审计、乐观并发和运行时图提交；
7. 可直接运行和观察上述流程的产品界面。

不实现 Drift Engine Module 02、通用工作流编辑器、通用 RAG、通用 IAM 或新的调度平台。

## 组件落位

```text
app/sources                     Phase A 规范身份与快照
        │
        v
app/compiler/tools              请求范围内的只读源工具
        │
        v
app/compiler/reasoner           ADK/Gemini reasoner + critic
        │
        v
app/compiler/models             IR、finding、canonical records
        │
        v
app/compiler/validation         V1–V7 固定顺序验证
        │
        v
app/compiler/review             完整性、矛盾、权威处置
        │
        v
app/compiler/canonicalization   稳定排序、去重、hash
        │
        v
app/compiler/service            无运行时副作用的编译流水线
        │
        ├── app/compiler/repository     编译审计工件
        └── app/compiler/acceptance     Runtime-only 乐观提交
                    │
                    v
             Continuum runtime graph
```

## 关键设计决定

### 1. 编译与接受严格分离

`CompilerService.compile` 只生成并持久化不可变 `CompilationResult`。它不创建运行时 Decision，也不改变 Mission 状态。`CompilationAcceptanceService.accept` 是唯一翻译规范 claims/edges 的入口，并验证：

- 结果 disposition 必须是 `ACCEPTED`；
- `expected_mission_revision` 仍等于当前 revision；
- `world_snapshot_id` 仍是该 Mission 的当前快照；
- 同一 `compilation_id` 重放不产生重复 Decision/边；
- 审计中可从运行时 Decision 反查 `compilation_id` 和 `compilation_hash`。

### 2. 模型只提议，确定性边界发证

Gemini 输出只包含局部 claim id 和它从工具返回值中复制的 refs。模型不能创建：

- canonical claim/edge/decision id；
- 编译状态；
- authority rank；
- source alias 解析；
- runtime lifecycle 状态。

Schema 错误只重试一次；未知 ref 不做模糊替换。所有状态与 canonical id 由编译器按固定算法生成。

模型执行层是 provider-neutral contract：Google ADK/Gemini 是最终规格要求的实现；在 Gemini 凭据尚不可用时，产品所有者授权先用 OpenAI Responses API 做真实模型验证。OpenAI 运行不得冒充 `Live Gemini` P0 证据，两类报告分别落盘。

OpenAI 验证有 **10 美元累计硬上限**：

- 默认使用支持 structured outputs 的成本敏感模型；
- 每次调用前按 max input/output 预留最坏成本，余额不足时不发请求；
- 每次调用后用响应 usage 的 input/cached/output token 分项记账；
- 预算 ledger 持久化且并发安全，累计到上限后确定性拒绝；
- 测试、报告和 UI 都显示预算上限、实际消耗及定价表版本。

### 3. 规范化稳定且可审计

规范化输入包括 validated draft、解析后的 fully-qualified refs、对应 source/fragment hashes、compiler version、validation policy version、prompt version。JSON 使用固定字段形状、UTF-8、排序键和紧凑分隔符。相同输入必须得到逐字节相同的 canonical output 和 `compilation_hash`。

Canonical ids 从 `compilation_hash + local identity` 推导，避免随机 UUID 破坏重复编译确定性；运行时最终 Decision id 仍由接受层基于编译 id 稳定生成。

### 4. 完整性与矛盾处置

Critic 只能从请求 allowlist 中选择 `candidate_ref`，或返回 `UNKNOWN_SOURCE_REQUIRED`。确定性层再次验证 critic refs，不能接受模型虚构值。

- CRITICAL missing dependency：`REJECTED_INCOMPLETE_DEPENDENCIES`；
- SUPPORTING omission：warning，不阻断；
- blocking unresolved question：不允许接受；
- 有可配置确定性 precedence：记录矛盾及 resolution，继续；
- 无 precedence 的 material contradiction：`NEEDS_HUMAN_REVIEW`；
- 已确定直接违反权威策略的高风险结果：`REJECTED_CONTRADICTION`。

不通过平均 confidence 解决矛盾。

### 5. 持久化与 Cloud 适配

编译工件使用独立 repository protocol，提供 in-memory、SQLite 和 Firestore 实现。SQLite 是本地默认，Firestore 通过现有 `CONTINUUM_RUNTIME_STORE=firestore` 组合启用。编译事件写入独立 outbox 类型，运行时接受成功后才产生 `decision.created`。

### 6. 评估是产品代码

`bench/dependency/cases/` 提交 120 个真值案例，三个域各 40 个。每个案例包含源目录、世界快照、请求、真值、至少一个 mutation。语料显式覆盖：

- 10 prompt-injection；
- 10 misleading near-match；
- 10 obsolete revision trap；
- 10 contradictory-authority；
- 10 omission。

Runner 分开输出 deterministic/fake 集成证据和 credential-gated live Gemini 证据。mock 结果永远不能把 `live_gemini` 行标为 PASS。报告同时给出文档级基线、单阶段 reasoner、完整双阶段编译器的指标。

在 Gemini 凭据可用前，先运行同一 corpus 的 live OpenAI 套件验证 prompt/schema/critic 方法与预算；该结果进入独立 `live_openai` evidence 行，不覆盖 `live_gemini`。

### 7. 产品交付面

现有 Mission Control 增加 `Compiler Lab`，展示：

- 请求与 world snapshot；
- reasoner 产生的 atomic claims；
- exact source fragment dependencies；
- validation/critic/contradiction findings；
- disposition、compilation hash；
- 接受到运行时后的 Decision 与审计链接；
- 当前执行模式（真实 Gemini 或本地 fixture）以及真实模型证据是否存在。

本地 fixture 模式用于可重复演示，但 UI 和报告必须明确标记，不能伪装为 live evidence。

## 失败语义

所有确定性失败使用稳定 code；API 用 422 表示 schema/input，404 表示不存在，409 表示状态、快照、并发或 disposition 冲突。失败的编译工件仍可查询并审计，但永不产生运行时 mutation。

## 完成定义

完成必须同时满足 Module 01 P0 matrix：真实 Gemini、120 corpus、所有指标、并发接受、审计链接、注入案例和全量测试。若凭据或外部 Cloud 权限缺失，代码可以完成但模块状态必须明确保持 `BLOCKED`，不得称为产品已完成。
