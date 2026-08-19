# Continuum Compiler Lab — 产品界面设计

**日期：** 2026-08-19
**状态：** 由当前 goal-mode 授权执行
**模式：** Extension；扩展既有 Mission Control，不改变现有路由、任务语义或 runtime 权限边界
**范围：** Module 01 Phase G 产品交付面；不把本地 fixture 冒充现场模型证据

## 1. 产品结果

Compiler Lab 把此前只能通过测试和 JSON 检查的 Semantic Dependency Compiler 变成一条可在浏览器内操作、审计和解释的产品流程：

```text
request
  → bounded model draft
  → deterministic reference validation
  → completeness / contradiction review
  → canonical compilation
  → runtime-only acceptance
```

用户必须能在一个工作面内回答：

1. 当前请求绑定了哪个 world snapshot？
2. 模型提出了哪些 atomic claims？
3. 每条 claim 精确依赖哪个不可变 source fragment？
4. 哪些内容由模型提出，哪些结果由确定性编译器发证？
5. 为什么 compilation 被接受、拒绝或转人工审阅？
6. 接受后 runtime 创建了什么 Decision / Claim / Evidence 关系？
7. 当前是否存在真实模型证据；若不存在，为什么是 `BLOCKED`？

## 2. 语义与权限边界

- 模型只提议 draft、claim、局部 dependency ref 和 critic finding。
- compiler 负责验证、处置、规范 ID、排序和 compilation hash。
- runtime 仍是唯一可以创建运行时 Decision、Claim 和边的主体。
- 浏览器不持有 `X-Continuum-Runtime-Capability`。
- 产品演示的“提交到 Runtime”走显式的 demo orchestrator endpoint；该 endpoint 只接受由服务器生成并登记的 reference scenario，内部调用同一 `RuntimeAcceptanceService`，不能用于任意 compilation。
- 通用 `/api/compiler/{request_id}/accept` 继续要求 runtime capability；CORS 不允许浏览器提交该 header。
- 没有 OpenAI/Gemini 凭据时，现场模型证据必须显示 `BLOCKED`。确定性 reference fixture 只能标记为 `DETERMINISTIC_REFERENCE`。
- OpenAI 现场验证使用持久化预算账本，累计硬上限 `$10.00`。缺少凭据时不得消费；余额不足时调用前拒绝。

## 3. Design Read

```yaml
artifact: enterprise compiler review surface
audience: hackathon judges, enterprise architects, runtime reviewers
visual-language: clinical review + CAD provenance drafting
mode: extension
visual-variance: 5
motion-intensity: 2
information-density: 9
asset-dependence: 1
brand-fidelity: 9
register: 8
```

刻度对应的实现后果：

- **方差 5：** 现有顶栏、IBM Plex 字体、浅色 token 和 Mission Control 交互保持不变；Compiler Lab 内部使用一条新的 provenance spine，而非重做全站。
- **动效 2：** 只有提交后的状态反馈和短距离选中变化，不使用循环动画、扫描光或回放奇观。
- **密度 9：** 同屏展示 source、claim、finding、hash 和 runtime link；用固定分区与渐进披露控制负荷。
- **素材 1：** 产品价值来自真实结构化数据，不需要摄影或装饰插画。
- **保真 9：** 不更改 Mission Control 主屏的信息架构、导航名称和既有语义色。
- **语域 8：** 无第二人称、无拟人动词；标题使用指标短语或阶段名称；每个预算/指标值同时显示单位与口径。

## 4. 视觉系统

### 主风格与辅助风格

- **主风格：Clinical Medical 68%。** 固定阅读区与操作区、明确严重度、极高对比、不可逆操作边界、状态文字不依赖颜色。
- **辅助风格：CAD & Drafting 32%。** exact refs、hash 和 version 采用尺寸标注式排布；provenance 路径使用正交细线、刻度和稳定锚点。
- **风格强度：55%。** 专业工具优先；识别度集中在 provenance spine，不把每个组件做成概念海报。
- **上一个项目主风格：Rail Dispatch。** 本次不使用轨道、站点、信号灯或路线隐喻。

### 被排除的候选

1. **SOC & Command：** 通常依赖深色和告警海洋，会把 dependency 审阅错误地表达成事故响应，并制造告警疲劳。
2. **Bento：** 等权卡片会拆散 source → claim → decision 的因果方向，无法稳定表达 exact ref 和 runtime boundary。
3. **Neo-Swiss：** 超大标题和破网格会牺牲专业工具密度，而且属于用户已明确看腻的默认吸引子。

### 五个视觉常量

- **圆角：** 控件 2px；面板 4px；仅 compact status token 可以 999px，但默认状态标签仍使用 2px。
- **描边：** 常规 1px `#D6D8D2`；选中项 2px `#18201D`；critical 阻断 2px `#C74B36`。
- **阴影：** 无常规阴影；runtime acceptance 确认浮层允许 `0 8px 24px rgba(24,32,29,.08)`。
- **间距：** 4 / 8 / 12 / 16 / 24 / 32px；主工作面采用 8px 基线。
- **字阶：** 9 / 10 / 12 / 14 / 20 / 30px；正文 12–14px，ID、hash、ref 使用 9–10px mono。

### 色板与字体

- Canvas `#F4F3EF`
- Paper `#FCFBF8`
- Ink `#18201D`
- Muted `#66706A`
- Rule `#D6D8D2`
- Accepted / runtime-owned `#167A5A`
- Critical / rejected `#C74B36`
- Review / blocked `#B87917`
- Model-proposed / informational `#396A8C`
- 字体继续使用 IBM Plex Sans；ID、hash、version、ref、预算值使用 IBM Plex Mono。

颜色只承担冗余信号：所有状态同时具备文字、边框/线型和图标或前缀。

## 5. 文案语域

**语域：8 / 专业报告。**

- 禁用“AI 想了想”“看起来没问题”“我们帮你找到”等对话式或拟人化文案。
- 使用 `Compilation disposition: ACCEPTED`、`Critical omissions: 0`、`World snapshot: ws-acme-v13`。
- 预算同时显示 `$0.00 consumed / $10.00 cumulative cap`，并在邻近位置显示 `Pricing table version`。
- `BLOCKED` 必须给出事实原因，如 `OPENAI_API_KEY not configured`，不得写成模糊的“暂不可用”。
- fixture 模式写为 `Execution mode: DETERMINISTIC_REFERENCE`，不得写 `AI compiled`。

## 6. 页面结构

### 6.1 顶级导航

既有 utility rail 新增第四个视图 `Compiler Lab`。现有三项名称、Reset 行为和 Mission URL 契约不变。进入 Compiler Lab 后仍能返回当前 Mission，不改变 local storage 指针。

### 6.2 Evidence header

工作面顶部固定展示：

- `SEMANTIC DEPENDENCY COMPILER / MODULE 01`
- 当前 scenario 名称与 decision intent
- execution mode
- live OpenAI evidence 状态
- live Gemini evidence 状态
- OpenAI 累计预算消耗 / `$10.00` cap / pricing table version
- 主操作：`Run reference compilation`；已编译且 `ACCEPTED` 后变为 `Commit accepted compilation to Runtime`

### 6.3 Immutable stage ruler

横向固定阶段尺：

```text
REQUESTED → DRAFT_RECEIVED → VALIDATED → REVIEWED → COMPILED → RUNTIME_ACCEPTED
```

每段显示确定性 owner：`MODEL PROPOSAL` 只覆盖 draft / critic；其余标为 `COMPILER` 或 `RUNTIME`。进行中状态不移动阶段位置。

### 6.4 主工作面

桌面端三栏，但不是三张卡片：

1. **Source register（264px）：** world snapshot、允许的 artifact revision、exact fragment refs、fragment hash。选择 source ref 会高亮所有引用它的 claim。
2. **Provenance drafting surface（自适应主栏）：** atomic claims 依序展开；每条显示 claim type、materiality、statement、source anchor、canonical claim ID。claims 汇入 decision bar，形成唯一的视觉签名 provenance spine。
3. **Verification ledger（320px）：** validation findings、critic findings、contradiction resolution、unresolved questions、disposition、compilation hash。阻断 finding 固定在顶部，不能被折叠隐藏。

底部是 **Runtime receipt**：accepted Decision ID、Claim IDs、Evidence IDs、audit link、mission revision、world snapshot。未接受时保留相同几何，显示明确空态。

### 6.5 Scenario selector

Reference fixture 提供四个明确标注的场景，每个都走真实 compiler pipeline：

1. `Authorized access / ACCEPTED`
2. `Missing governing clause / REJECTED_INCOMPLETE_DEPENDENCIES`
3. `Conflicting authorities / NEEDS_HUMAN_REVIEW`
4. `Obsolete Policy v12 ref / REJECTED_STALE_SOURCE`

切换场景会创建新的 request namespace，不覆盖旧 compilation。只有第一个场景显示 runtime commit 操作；后三个显示阻断原因且不会产生 runtime mutation。

## 7. 唯一视觉签名：Provenance Spine

Source register 的 fragment anchor 通过正交 1px line 连接到 claim 左侧固定锚点；claim 再连接到 decision bar。视觉行为：

- critical = 2px solid；supporting = 1px solid；contextual = 1px dotted；
- stale / invalid = broken vermilion；
- model-proposed 区域使用蓝色边注 `PROPOSED`；
- canonicalized 后，同一结构增加绿色 `VERIFIED` 尺寸标记；
- 不使用自由拖拽、不模拟 workflow builder；图是只读审阅面。

这个 spine 是页面唯一允许的非通用视觉风险。其余组件保持安静、规整和高可读。

## 8. 状态与无障碍

- **Empty：** 固定工作面骨架 + `No compilation selected` + `Run reference compilation`。
- **Loading：** 保留全部栏宽；stage ruler 标记当前操作；主操作 disabled；`aria-busy=true`。
- **Success：** disposition 与 hash 同时出现；成功不是 confetti。
- **Failure：** 保留上一个可查询工件；错误带稳定 code、Retry，且不清空 source/claim 内容。
- **Blocked evidence：** `BLOCKED` + credential/budget/cloud reason；不渲染为失败 compilation。
- **Human review：** amber border + `No runtime mutation permitted`。
- **Responsive：** ≥1180px 三栏；760–1179px source register 在上、claims + ledger 双栏；<760px 按 Source → Claims → Findings → Runtime receipt 顺序单栏，导航可见，hash/ref 允许水平滚动但不截断复制值。
- 所有操作键盘可达；44px 最小触控目标；focus ring 3px；状态不只靠颜色；`prefers-reduced-motion` 下取消所有非必要 transition。

## 9. 参考研究

- Microsoft Foundry Trace Replay 将 trajectory tree、步骤详情、原始 metadata 和 evaluation 结果放在同一审阅面；Compiler Lab 借鉴“选择一个步骤、邻近查看细节”的结构，但不把模型 trace 等同于确定性 provenance：<https://learn.microsoft.com/en-us/azure/foundry/observability/how-to/trace-agent-replay>
- Microsoft Foundry Evaluation Results 同时展示 aggregate 指标与 sample-level query / response / ground truth / explanation；Compiler Lab 同样把 disposition 总结和逐条 finding 分层：<https://learn.microsoft.com/en-us/azure/foundry/how-to/evaluate-results>
- OpenLineage / Marquez 把 lineage graph、run metadata 和 history 分开呈现；Compiler Lab 借鉴精确 lineage 与 detail 的并置，但主语是 Decision provenance，不是 data pipeline：<https://openlineage.io/getting-started/>
- 既有 Continuum Mission Control 保持 runtime narrative 入口；Compiler Lab 只增加编译审阅面，不取代 Mission Route。

## 10. 工程验收

### 前端行为

- `Compiler Lab` 可从当前 Mission 打开和返回。
- reference compilation 显示 world snapshot、atomic claims、exact refs、findings、disposition、hash。
- 被拒绝或需人工审阅的 compilation 不出现 runtime commit 操作。
- accepted fixture 通过服务器 demo orchestrator 接受后显示 runtime Decision / Claim / Evidence / audit receipt。
- `DETERMINISTIC_REFERENCE`、OpenAI `BLOCKED`、Gemini `BLOCKED` 和 `$10.00` cap 不能被隐藏。
- loading、API error、blocked、success、human review 和移动端均有自动化测试。

### 后端行为

- 默认 compiler critic 必须 fail closed；没有真实或显式 fixture reviewer 时不得把缺失依赖静默判为 accepted。
- demo scenario 数据不得进入 compiler 核心规则；它们只能存在于 demo fixture/composition 层。
- demo accept endpoint 只接受服务器登记的 accepted reference compilation，并调用现有 runtime acceptance service。
- 通用 accept endpoint 的 runtime capability 安全测试继续通过。
- 现场 OpenAI/Gemini 状态来自实际凭据和证据工件，不来自 UI 常量。

### 浏览器视觉验收

- 对照生成的 benchmark 检查 1440px 与 320px 截图。
- 程序化检查主三栏、stage ruler 和 runtime receipt 的边界与对齐。
- 检查无横向页面溢出、导航未截断、exact ref 可完整读取、console 无 warning/error。
- 五维评审重点：功能性、工艺质量、视觉层级；原创性只由 provenance spine 承担。
