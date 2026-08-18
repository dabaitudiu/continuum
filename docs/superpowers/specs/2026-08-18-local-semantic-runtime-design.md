# Continuum 本地语义运行时设计

**状态：** 已批准（goal 模式持续授权）

**日期：** 2026-08-18

**范围：** 完整产品路线的里程碑 A；建立可持久化、可恢复、可迁移到 Firestore 的确定性运行时内核。

## 1. 决策

Continuum 的完整产品按以下顺序交付：

1. 本地持久化语义运行时：Mission、WorkItem、Commitment、Decision Graph、Side Effect Ledger、Audit/Outbox。
2. 本地完整浏览器产品：真实演示 vendor onboarding 从等待、策略漂移、补证据到激活。
3. 接入三个 Google ADK/Gemini agent：Vendor、Security、Procurement。
4. 迁移至 Firestore、Pub/Sub、Cloud Run/Agent Runtime，并加入 OpenTelemetry。
5. 完成云端三次稳定演示、托管 URL 与参赛材料。

本规格只实现第 1 项，但其接口和数据边界必须服务最终产品，不能做成一次性模拟。已有 Phase G 决策图和失效传播逻辑保留并纳入新的 Mission aggregate。

## 2. 目标与验收信号

里程碑 A 必须证明：

- 进程重启后，Mission、WorkItem、Commitment、Decision Graph、Side Effect 和 Audit history 均可恢复。
- 不匹配的外部事件不会唤醒任务；匹配的 pen-test 事件只满足一次 Commitment。
- 同一个 event/request 重放不会产生额外 WorkItem、状态迁移、审计记录或副作用。
- Policy v12 → v13 仍会确定性地令 D42 与下游分支失效，并只重新调度受影响分支。
- 新判断以新 Decision 取代旧 Decision；旧 Decision 保留历史并进入 `SUPERSEDED`，不得原地改写为新的有效结论。
- 只有 `VALID` Decision 能授权副作用；未知执行结果必须先 reconciliation，禁止盲目重试。
- 两个并发写入者不能静默覆盖彼此；较晚提交者得到 revision conflict。
- 已有 Phase G API 和测试继续通过。

## 3. 组件边界

### 3.1 MissionStateMachine

只负责 Mission 状态迁移和迁移前置条件。它不访问数据库、不调 agent、不执行副作用。

Mission 状态：

- `CREATED`
- `RUNNING`
- `WAITING`
- `REVALIDATING`
- `BLOCKED`
- `COMPLETED`
- `FAILED`
- `CANCELLED`

`COMPLETED`、`FAILED`、`CANCELLED` 为终态。Demo reset 创建新 mission namespace，不复活终态 Mission。

### 3.2 WorkScheduler

根据 canonical state 计算可运行 WorkItem，并生成 dispatch proposal。它不把 agent 输出当作 canonical state，也不允许 agent 自己推进 Mission。

WorkItem 状态：

`PENDING → DISPATCHED → RUNNING → SUCCEEDED | WAITING | FAILED | CANCELLED`

每次成功 dispatch 才增加 `attempt`。重复的 request id 返回首次结果，不增加 attempt。

### 3.3 CommitmentService

管理运行时对未来外部事实的等待：

- `OPEN → SATISFIED | EXPIRED | CANCELLED`
- 每个 `WAITING` WorkItem 必须关联至少一个 `OPEN` Commitment。
- 事件必须同时匹配 event type 和结构化 predicate 才可满足 Commitment。
- 一个 Commitment 只能由第一个匹配事件满足；后续重放返回已有结果。

### 3.4 InvalidationService 与 RevalidationService

复用 Phase G 已验证的图遍历语义：外部 artifact 版本变化引发直接失效、关键边下游传播以及 selective revalidation。扩展 Decision 生命周期以支持 `INVALID` 和 `SUPERSEDED`，但不改变 Phase G 已通过的 `VALID → STALE → REVALIDATING` 行为。

重新验证不得修改旧 Decision 的结论。成功时创建新 Decision，并以 `supersedes_decision_id` 指向旧 Decision；旧 Decision 转为 `SUPERSEDED`，依赖边改为引用新 Decision。

### 3.5 SideEffectLedger

所有外部写操作先进入账本，再由执行器处理。状态为：

- `INTENDED`
- `EXECUTING`
- `COMMITTED`
- `FAILED_RETRYABLE`
- `FAILED_FINAL`
- `RECONCILIATION_REQUIRED`

账本使用稳定 `idempotency_key`，在一个 Mission 内唯一。只有当前授权 Decision 为 `VALID` 且所有前置条件仍成立时，`INTENDED` 才能进入 `EXECUTING`。执行结果未知时进入 `RECONCILIATION_REQUIRED`，确认外部状态前不得重试。

### 3.6 RuntimeCoordinator

这是唯一可组合 canonical transition 的应用层入口。每个 command/event 的流程是：

1. 检查 inbox 幂等记录。
2. 读取 RuntimeSnapshot 和 revision。
3. 调用纯领域服务生成 RuntimeMutation。
4. 校验跨实体不变量。
5. 在一个仓储事务中提交 entity changes、audit events、inbox result 和 outbox events。
6. 返回提交后的 read model。

HTTP route、agent adapter、simulator 和未来 Pub/Sub consumer 均只能调用 RuntimeCoordinator，不得直接写 repository。

### 3.7 AuditLedger 与 Transactional Outbox

每个 canonical transition 追加一条不可变 AuditEvent。`event_sequence` 在 Mission 内严格单调递增，用于 UI timeline 和可重复验证。

需发布到 Pub/Sub 的事件先和状态事务一起写入 outbox。里程碑 A 只实现 outbox 的持久化和读取契约；实际 publisher 在云端里程碑实现。

## 4. Aggregate 与数据模型

`RuntimeSnapshot` 是一次协调所需的一致性视图，包含：

- `Mission`
- `WorkItem[]`
- `GraphSnapshot`
- `Commitment[]`
- `SideEffectRecord[]`
- `revision`
- 最近一次 command/event result（由 inbox 查询）

Canonical entity 仍保持独立、可查询，而不是把整个 aggregate 存为一个不可查询 JSON blob。

SQLite 表：

- `missions`
- `work_items`
- `world_artifacts`
- `evidence_nodes`
- `decisions`
- `actions`
- `dependency_edges`
- `commitments`
- `side_effects`
- `inbox_messages`
- `outbox_messages`
- `audit_events`
- `dispatch_records`

复杂 payload 可用 JSON 列保存，但 identity、mission id、status、revision、sequence、idempotency key 与时间字段必须是可索引列。表命名和实体边界与最终 Firestore collections 对齐。

## 5. 仓储契约与事务

仓储公开两个核心操作：

```python
load(mission_id: str) -> RuntimeSnapshot
commit(
    mission_id: str,
    expected_revision: int,
    mutation: RuntimeMutation,
) -> RuntimeSnapshot
```

`RuntimeMutation` 明确列出 entity upserts、audit append、inbox completion 和 outbox append；不使用数据库事务内部 callback，从而使 SQLite 和未来 Firestore adapter 共享契约。

提交规则：

- `expected_revision` 必须等于当前 Mission revision。
- 所有 entity change、audit、inbox、outbox 在同一事务中成功或全部回滚。
- 成功提交后 revision 恰好加一。
- inbox 唯一键为 `(mission_id, message_id)`；保存原始结果摘要，重放时返回相同业务结果并标记 `duplicate=true`。
- side effect 唯一键为 `(mission_id, idempotency_key)`。
- audit 唯一键为 `(mission_id, event_sequence)`。

提供两种实现：

- `InMemoryRuntimeRepository`：单元测试与 repository contract test。
- `SQLiteRuntimeRepository`：本地开发默认实现，使用文件数据库并证明跨进程实例恢复。

现有 `GraphRepository` 在迁移期保留。Phase G route 先通过 compatibility adapter 访问新 repository；迁移完成后旧 in-memory 实现只作为兼容测试 fixture。

## 6. 状态语义

### 6.1 Mission

- `CREATED --start--> RUNNING`
- `RUNNING` 无可运行工作且存在开放 Commitment 时进入 `WAITING`。
- 任一仍被消费的 Decision 变为 `STALE` 时进入 `REVALIDATING`。
- 安全前置条件无法满足且无可等待的外部事实时进入 `BLOCKED`。
- 所有必需工作成功且所需副作用均为 `COMMITTED` 时进入 `COMPLETED`。
- `WAITING` 收到匹配事件后进入 `RUNNING` 或 `REVALIDATING`。
- `REVALIDATING` 产生新的有效 superseding Decision 后进入 `RUNNING`；若缺证据则进入 `WAITING`；无法安全继续则进入 `BLOCKED`。
- `BLOCKED` 的 blocker 被显式解决后才可回到 `RUNNING` 或 `REVALIDATING`。

### 6.2 原子事件处理

匹配事件必须在一次提交中完成：记录 inbox、满足 Commitment、创建新的 `PENDING` WorkItem、更新 Mission、追加 AuditEvent 与 OutboxMessage。任何一步失败均不得产生部分结果。

不匹配事件可被记录为已处理，但不得改变 Commitment、WorkItem 或 Mission 状态。重复事件返回首次处理结果，不追加第二条业务审计记录。

### 6.3 拒绝条件

以下情况整体拒绝且不产生部分写入：

- 非法 Mission、WorkItem、Commitment 或 SideEffect 状态迁移。
- revision 不一致。
- `WAITING` WorkItem 不存在开放 Commitment。
- 使用 `STALE`、`INVALID`、`REVALIDATING` 或 `SUPERSEDED` Decision 授权副作用。
- 对 `EXECUTING` 或结果未知的副作用直接重试。
- event payload 无法通过对应 schema 校验。

## 7. API 契约

里程碑 A 新增或完成：

- `POST /api/missions/demo`：创建新的 vendor onboarding Mission。
- `POST /api/missions/{id}/start`：以 request id 幂等启动。
- `GET /api/missions/{id}`：Mission summary、revision、当前 runnable/waiting/blocking 数量。
- `GET /api/missions/{id}/timeline`：按 `event_sequence` 返回 AuditEvent。
- `GET /api/missions/{id}/commitments`：返回开放与历史 Commitment。
- `POST /api/events`：统一接收 schema-validated domain event envelope。

继续兼容 Phase G：

- `POST /api/demo/reset`
- `POST /api/demo/policy/upgrade`
- `GET /api/missions/{id}/graph`
- `POST /api/missions/{id}/revalidate`

所有 mutation request 都包含稳定 request/event id。业务错误返回固定 `{code, message}`：

- `MISSION_NOT_FOUND`
- `INVALID_MISSION_TRANSITION`
- `INVALID_WORK_TRANSITION`
- `REVISION_CONFLICT`
- `COMMITMENT_INVARIANT_VIOLATION`
- `EVENT_SCHEMA_INVALID`
- `STALE_AUTHORIZATION`
- `SIDE_EFFECT_RECONCILIATION_REQUIRED`

重复 mutation 返回成功状态和 `duplicate=true`，而不是把正常重放当成冲突。

## 8. 错误处理与可观测性

领域层用有稳定 code 的 typed exception；FastAPI 只负责映射 HTTP status。404 用于不存在资源，409 用于状态/revision 冲突，422 用于 event schema，500 只用于未分类错误。

每个 audit/outbox record 都包含 `mission_id`、`correlation_id`、`causation_id` 和可选 `trace_id`。里程碑 A 不引入完整 OTel exporter，但字段从第一天存在，避免云端迁移时重写事件模型。

SQLite 不可写、schema migration 失败或事务提交失败时，API 返回明确错误且 canonical state 保持原样。

## 9. 测试策略

按 TDD 实现，测试层次如下：

1. 状态机表驱动单元测试：覆盖每个合法和非法迁移。
2. Commitment matching：错误事件无效、正确事件满足一次、重复事件不重复唤醒。
3. SideEffectLedger：有效授权、拒绝 stale authorization、幂等提交、未知结果 reconciliation。
4. Repository contract：同一组测试运行于 in-memory 和 SQLite。
5. SQLite restart integration：关闭第一个 repository 实例，再用同一数据库文件恢复完整 Mission。
6. 并发测试：两个 writer 使用相同 revision，只有一个成功。
7. 原子性测试：注入提交失败，entity/audit/inbox/outbox 均不产生部分写入。
8. Phase G regression：现有 23 个 backend tests 全部保留。
9. API integration：create/start/read/timeline/commitments/events 及稳定错误码。

里程碑 A 完成门：所有 backend tests 通过，branch-aware coverage 不低于当前 98%，并提供一次真实 SQLite restart 的测试证据。

## 10. 明确延后

以下内容属于后续里程碑，不在本次实现中伪造：

- React Mission Control 的完整交互与最终视觉设计。
- Gemini 推理与三个 Google ADK agent。
- Firestore、Pub/Sub、Cloud Run、Agent Runtime 和 OTel exporter。
- 企业系统真实副作用；本阶段只提供确定性 ledger 与 fake executor contract test。
- 通用 workflow editor、agent builder、IAM、memory platform 或 Temporal replacement。

本地 adapter 不是最终云能力的 mock 宣称。最终产品只有在真实 Google 技术栈接入、云端部署与端到端演示均有证据时才算完成。

## 11. 与既有 Phase G 的迁移顺序

1. 新增 runtime domain models 与纯状态服务，不修改 Phase G 行为。
2. 新增 RuntimeRepository contract 和 in-memory/SQLite implementations。
3. 用 RuntimeCoordinator 实现 Mission/Work/Commitment/SideEffect 命令。
4. 将 canonical Phase G graph 作为 demo Mission 的 graph 部分持久化。
5. 通过 compatibility adapter 让旧 route 使用新 repository，保持 response shape。
6. 验证全部回归和 restart/concurrency/atomicity tests 后，删除不再被生产路径使用的重复状态写逻辑。

这一路径避免“大爆炸”改写，并确保每次提交都能保持已通过的 falsification gate。
