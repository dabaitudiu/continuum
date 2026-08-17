# Continuum

## A Runtime for Long-Lived Enterprise Agents

### Hackathon Track

**Fortified Enterprise Fleet**

重点能力：

**Core Execution & State**
- Agent Runtime
- Memory Bank

辅助覆盖：

- Agent Registry
- Agent Identity
- Agent Gateway
- Model Armor
- Agent Observability

---

# 1. Executive Summary

今天绝大多数 AI Agent 都隐含了一个假设：

> Agent 执行任务期间，世界基本保持不变。

这个假设对于持续几十秒或几分钟的 Agent 尚且勉强成立。

对于持续数天甚至数周的企业 Agent，则完全不成立。

一个 Agent 在第 1 天做出的决定，可能依赖：

- 当时的企业政策
- 当时的数据
- 当时的用户权限
- 当时的供应商状态
- 当时的工具结果
- 当时的其他 Agent 承诺

到了第 15 天，这些前提可能已经变化。

传统 durable workflow 可以让 Agent：

> 从 crash 前的位置继续运行。

但它无法回答更加重要的问题：

> **它还应该从那个位置继续吗？**

Continuum 是一个面向长生命周期 Enterprise Agents 的 execution runtime。

它不仅持久化 Agent 的执行状态，还持久化：

- Decision
- Evidence
- Dependency
- Commitment
- Side Effect
- Policy Version
- Identity Context
- Artifact Provenance

当底层事实发生变化时，Continuum 可以计算：

> 哪些过去的决策已经失效？

然后只重新执行受影响的部分，而不是：

- 无脑从 checkpoint 继续；
- 或者把整个任务从头执行一遍。

核心目标不是简单的：

**Durable Execution**

而是：

# Semantically Safe Continuation

---

# 2. Problem

假设一家企业使用 Agent 完成供应商 onboarding。

任务可能持续 20 天。

Day 1：

```text
Vendor submits application.
```

Agent 完成：

```text
identity verification
security questionnaire
financial review
contract review
```

并产生：

```text
Decision:
Vendor security risk = ACCEPTABLE
```

该决定基于：

```text
security_policy:v12
SOC2-report:hash-A31
vendor-profile:revision-7
```

然后 Agent 等待采购经理批准。

---

Day 12，企业更新安全政策：

```text
security_policy:v12
        ↓
security_policy:v13
```

新政策规定：

> 所有处理 customer PII 的供应商必须提交额外 penetration test。

普通 durable runtime 在 Day 14 收到经理批准后会：

```text
resume()
↓
continue from checkpoint
↓
create vendor
```

技术上它没有犯任何错误。

但业务上它已经错了。

因为：

```text
security approval
```

依赖的政策已经过期。

---

# 3. Core Thesis

长期 Agent 最大的问题之一并不是：

> 能不能恢复？

而是：

> **恢复之后，过去的世界模型是否仍然有效？**

Continuum 将 Agent 的执行建模为：

```text
State
+
Decisions
+
Dependencies
+
Commitments
+
Side Effects
```

任何 Decision 都不是一段孤立的文本。

例如：

```text
Decision D42
VendorSecurityApproved

depends_on:
  security_policy:v12
  soc2_report:sha256(...)
  vendor_profile:rev7

produced:
  security_clearance:approved
```

当：

```text
security_policy:v12 → v13
```

Continuum 可以发现：

```text
D42
STALE
```

继而传播：

```text
D42
 ↓
ProcurementApproval
 ↓
VendorActivation
```

只有真正受影响的 execution branch 被 invalidated。

---

# 4. Product Principle

Continuum 不试图打造：

> Another general-purpose multi-agent framework.

Google ADK 仍负责：

- Agent 定义
- LLM reasoning
- Tool invocation
- Multi-agent orchestration

Gemini 仍负责：

- Planning
- Reasoning
- Classification
- Replanning
- Decision generation

Continuum 专门解决：

> **Long-lived Agent Execution Semantics**

即：

```text
Can this agent safely continue?
```

---

# 5. Core Objects

## 5.1 Run

一个长期存在的业务任务。

```text
Run
id
mission
created_at
status
owner
deadline
```

示例：

```text
Onboard Vendor Acme Ltd.
```

---

## 5.2 Decision

Agent 做出的业务判断。

```text
Decision
id
type
result
reason
created_by
created_at
```

例如：

```text
SecurityReviewPassed
```

Decision 必须显式声明 dependencies。

---

## 5.3 Evidence

支持 Decision 的事实。

例如：

```text
SOC2 report
API response
database record
policy document
human approval
tool output
```

Evidence 本身没有 verdict。

---

## 5.4 Dependency

表达：

> 一个 Decision 为什么成立。

例如：

```text
D42
 ├─ Policy:v12
 ├─ SOC2:A31
 └─ VendorProfile:r7
```

形成一张：

# Decision Dependency Graph

---

# 6. Commitment Memory

传统 Agent Memory 通常存：

```text
conversation
facts
preferences
summaries
```

Continuum 增加：

# Commitment

即：

> Agent 已经承诺未来要做什么。

例如：

```text
When vendor submits revised SOC2,
resume security review.
```

结构：

```text
Commitment

trigger:
  VendorDocumentUploaded

condition:
  document_type == SOC2

action:
  Resume(SecurityReview)

status:
  WAITING
```

这解决的是长生命周期 Agent 一个很现实的问题：

> 两周之后它是否还记得自己欠谁一件事？

---

# 7. Side Effect Ledger

企业 Agent 不只是产生文字。

它会：

```text
send email
create ticket
update database
approve payment
provision account
deploy software
```

因此 Runtime 需要区分：

```text
Decision

vs

External Side Effect
```

例如：

```text
ActionIntent
create_purchase_order

idempotency_key:
run42:purchase-order
```

执行成功：

```text
ActionCommitted
external_id: PO-18931
```

如果 Agent 此时 crash：

```text
kill -9
```

恢复后：

```text
Side Effect Ledger
        ↓
PO already committed
        ↓
DO NOT EXECUTE AGAIN
```

避免 duplicate side effects。

---

# 8. Semantic Resume

普通 Runtime：

```text
checkpoint
   ↓
resume
```

Continuum：

```text
checkpoint
   ↓
validate world
   ↓
validate policy
   ↓
validate permissions
   ↓
validate dependencies
   ↓
calculate stale decisions
   ↓
selective rewind
   ↓
resume
```

因此：

# Resume ≠ Continue

而是：

# Resume = Revalidate + Continue

---

# 9. Selective Revalidation

假设执行图：

```text
                 Vendor Intake
                      |
          +-----------+-----------+
          |                       |
     Financial                  Security
       Review                    Review
          |                       |
          +-----------+-----------+
                      |
                  Approval
                      |
                  Activation
```

只有：

```text
Security Policy
```

发生变化。

传统系统可能：

```text
restart entire workflow
```

Continuum：

```text
Financial Review      VALID
Vendor Intake         VALID

Security Review       STALE
Approval              STALE
Activation            BLOCKED
```

因此只重新运行：

```text
Security
→ Approval
→ Activation
```

---

# 10. Policy Drift

Policy 作为版本化 Artifact。

例如：

```text
security-policy:v12
security-policy:v13
```

Runtime 收到：

```text
PolicyUpdated
```

后计算：

```text
affected decisions
```

状态变成：

```text
VALID
STALE
REVALIDATING
INVALID
```

Gemini 可以帮助判断：

> 新旧 policy change 是否会影响某类 Decision。

但最终 invalidation 由 Runtime 显式记录。

---

# 11. Identity Drift

长期任务还会出现：

```text
employee leaves company
role changes
permission revoked
agent credential rotated
```

例如：

Day 4：

```text
ProcurementAgent

permission:
purchase.create
```

Day 18：

```text
purchase.create revoked
```

Agent 恢复时不能简单沿用旧 identity context。

Runtime 必须重新验证：

```text
principal
permissions
scope
policy
```

失败则：

```text
BLOCKED_NEEDS_AUTHORIZATION
```

---

# 12. Multi-Agent Model

Demo 中使用三个 Agent：

```text
Vendor Agent
Security Agent
Procurement Agent
```

由 Google ADK 实现。

职责严格隔离。

### Vendor Agent

负责：

```text
documents
vendor communication
profile
```

### Security Agent

负责：

```text
security review
policy interpretation
risk decision
```

### Procurement Agent

负责：

```text
commercial approval
vendor creation
```

Agent 之间不能直接任意调用外部系统。

全部经过：

```text
Agent Gateway
```

---

# 13. Agent Gateway

所有 Tool Invocation：

```text
Agent
  ↓
Gateway
  ↓
Identity Check
  ↓
Policy Check
  ↓
Idempotency Check
  ↓
Tool
```

Gateway 记录：

```text
principal
tool
arguments hash
policy version
timestamp
result
side effect
```

形成审计链。

---

# 14. Memory Bank

Memory 不做成一个 vector DB 大桶。

拆成五类。

### Working Memory

当前 workflow state。

### Episodic Memory

过去发生了什么。

### Decision Memory

为什么做过某个决定。

### Artifact Memory

当时基于哪些真实材料。

### Commitment Memory

未来仍需履行的义务。

其中后三个是产品重点。

---

# 15. Architecture

```text
                      Web Console
                           |
                           v
                      Cloud Run
                           |
                  Continuum Runtime
                           |
       +-------------------+-------------------+
       |                   |                   |
       v                   v                   v
   Google ADK         State Engine        Agent Gateway
       |                   |                   |
       v                   v                   v
 Gemini 3.5            Firestore          Tool APIs
       |
       |
 +-----+------+-------+
 |            |       |
Vendor     Security Procurement
Agent       Agent      Agent


                   Pub/Sub
                      |
        Async Events / Wakeups
                      |
              Continuum Runtime


                   Firestore
                      |
          +-----------+-----------+
          |           |           |
       Runs      Decisions     Evidence
       State     Dependencies  Commitments


               OpenTelemetry
                      |
                 Cloud Trace
```

---

# 16. Google Stack

比赛硬性要求自然满足。

### Gemini 3.5+

负责：

- planning
- policy reasoning
- document analysis
- replanning

### Google ADK

负责：

- agents
- tools
- delegation
- agent orchestration

### Cloud Run

运行：

```text
Runtime API
Agent workers
```

### Firestore

持久化：

```text
Run State
Decision Graph
Commitments
Evidence
Side Effect Ledger
```

### Pub/Sub

负责：

```text
long-lived wakeup
external events
async execution
```

### OpenTelemetry / Google Cloud Observability

记录：

```text
runs
agents
tool calls
waits
resumes
revalidation
```

---

# 17. Demo Scenario

产品 Demo：

# Vendor onboarding

用户发起：

```text
Onboard Acme Analytics
```

Agent 自动：

```text
collect documents
↓
security review
↓
financial review
↓
procurement approval
```

Security Agent 得出：

```text
SECURITY APPROVED
```

UI 显示：

```text
Decision #42

based on:
SOC2.pdf
Vendor Profile r7
Security Policy v12
```

Agent 随后：

```text
WAITING FOR PROCUREMENT APPROVAL
```

---

# 18. Demo Twist

这时候人为触发：

```text
Security Policy
v12 → v13
```

新政策：

```text
AI vendors handling customer data
must provide penetration testing evidence.
```

UI 立即显示：

```text
POLICY DRIFT DETECTED
```

dependency graph：

```text
Policy v12 ✕
      |
Decision D42
      |
Security Approval
      |
Procurement Approval
      |
Vendor Activation
```

状态：

```text
D42 → STALE
```

Runtime 自动：

```text
invalidate Security Review
preserve Financial Review
block Activation
```

Security Agent 被重新唤醒。

Gemini 读取：

```text
Policy v13
```

发现缺少：

```text
Penetration Test
```

创建 Commitment：

```text
WAIT_FOR vendor_pen_test
```

---

# 19. Long-Time Compression

真实世界可能等 7 天。

Demo 中点击：

```text
Simulate: 7 days later
```

上传：

```text
penetration-test.pdf
```

Pub/Sub event：

```text
VendorDocumentUploaded
```

Runtime：

```text
match commitment
↓
wake Security Agent
↓
restore context
↓
revalidate
```

Security Review：

```text
PASS
```

Procurement workflow 恢复。

最终：

```text
Vendor Activated
```

---

# 20. Crash Recovery Demo

为了证明不是普通 workflow UI：

执行中直接：

```text
kill worker
```

页面：

```text
WORKER LOST
```

新实例启动：

```text
RUN RECOVERED
```

继续原 execution。

同时 Side Effect Ledger 表明：

```text
vendor email already sent
```

因此不会发送第二封。

这是一个很有说服力的技术 Demo。

---

# 21. UI

主界面不是 Chat UI。

而是：

# Mission Control

包含：

### Timeline

```text
DAY 1
Security review completed

DAY 4
Waiting for procurement

DAY 11
Policy changed

DAY 11
Decision D42 invalidated

DAY 11
Security agent resumed

DAY 18
New evidence received

DAY 18
Mission completed
```

### Dependency Graph

可视化：

```text
Evidence
↓
Decision
↓
Decision
↓
Action
```

### Agent Status

```text
Vendor Agent       WAITING
Security Agent     RUNNING
Procurement Agent  BLOCKED
```

### Commitments

```text
WAITING:
penetration-test.pdf
```

### Policy Drift

突出显示：

```text
v12 → v13
```

### Audit Trail

每次：

```text
reason
tool
identity
policy
side effect
```

均可展开。

---

# 22. What We Are NOT Building

不做：

- 通用 Agent builder
- drag-and-drop workflow designer
- 通用 vector memory service
- 通用 scheduler
- Kubernetes replacement
- Temporal replacement
- Zapier replacement
- enterprise IAM replacement
- 完整 Agent Registry marketplace

这些都会导致 scope 失控。

---

# 23. Fleet Breadth Strategy

虽然创新集中在：

```text
Core Execution & State
```

仍应最低限度覆盖 Fleet。

### Registry

简单 Agent manifest：

```text
name
version
capabilities
permissions
owner
```

### Identity

每个 Agent 独立 principal。

### Gateway

统一 tool access layer。

### Model Armor

用于保护：

```text
documents
external tool responses
```

### Observability

OpenTelemetry traces。

这些属于 supporting infrastructure。

不要和 Runtime 抢工程时间。

---

# 24. Competitive Moat

单独来看以下能力都不新：

```text
checkpointing
memory
retry
agent orchestration
workflow persistence
```

Continuum 的区别是把：

```text
Decision provenance
+
world-state dependencies
+
commitments
+
side effects
+
policy/identity drift
```

统一纳入运行语义。

核心问题：

> **Can an old decision still be trusted?**

不是：

> Can the process restart?

---

# 25. Falsification Analysis

## Falsification 1

### “Temporal / Durable Workflow 已经解决这个问题。”

成立一半。

已有 workflow runtime 能处理：

```text
crash
retry
timeout
event
resume
```

如果 Continuum 只做到这些：

# 项目失败。

因此这些只能作为基础能力。

---

## Falsification 2

### “Agent Memory 系统已经可以记住这些信息。”

Memory 能保存：

```text
Policy v12 existed.
```

但保存事实与管理其对过去决策的有效性是不同问题。

Continuum 必须能够证明：

```text
policy changed
→ D42 stale
→ downstream decisions invalidated
→ execution branch revalidated
```

如果只能：

> 把旧信息重新塞给 Gemini，让 Gemini自己想怎么办，

那么：

# 项目失败。

---

## Falsification 3

### “这其实就是 dependency graph。”

如果核心实现最终只是：

```text
DAG invalidation
```

也不够。

必须同时体现：

```text
LLM-generated decisions
real external side effects
identity/policy evolution
asynchronous waiting
cross-agent commitments
```

否则只是 build system 思路换皮。

---

## Falsification 4

### “这不是 AI 问题，普通 workflow engine 就能做。”

这是最大的攻击点。

回应不能是：

> 我们用了 Gemini。

真正答案应当是：

企业 Agent 的 dependency 很多不是程序员预先定义的。

例如 Gemini 在审核 document 后形成：

```text
Decision:
vendor can access PII

Dependencies:
policy section 7.3
data residency answer
SOC2 control CC6.1
contract clause 12
```

这种 dependency 是在 reasoning 时动态产生的。

Continuum 将：

```text
LLM reasoning
```

转化成：

```text
machine-trackable execution dependency
```

这才是 Agent-specific contribution。

---

## Falsification 5

### “为什么不能每次 resume 都重新跑整个任务？”

当然可以。

所以 Continuum 的价值必须通过：

```text
cost
latency
side effects
human work
```

来展示。

例如：

一个 workflow 有 12 个已完成步骤。

政策只影响两个。

Continuum：

```text
re-run 2
preserve 10
```

而不是：

```text
restart 12
```

Demo 应明确展示这一点。

---

# 26. Kill Criteria

这是最重要的一部分。

以下任一情况出现，就应考虑砍掉项目。

### Kill #1

无法在 1 天内实现：

```text
dependency invalidation
→ selective rewind
```

说明核心机制过重。

---

### Kill #2

最终 Demo 必须靠大量解释才能让人明白：

> 为什么这和普通 workflow 不一样。

说明 product thesis 不够清楚。

---

### Kill #3

Policy 更新以后：

```text
Runtime
```

不能确定性展示：

```text
哪些 Decision stale
哪些仍 valid
```

只能让 Gemini自由发挥。

直接砍。

---

### Kill #4

4 分钟内无法完成：

```text
start
→ decision
→ wait
→ policy change
→ invalidate
→ resume
→ complete
```

说明 scope 太大。

---

### Kill #5

两天之后产品仍然主要是：

```text
backend logs + terminal
```

没有 Mission Control。

需要降 scope，把视觉 Demo 做出来。

---

# 27. MVP

真正必须完成的只有：

1. Persistent Run
2. Decision record
3. Evidence record
4. Dependency graph
5. WAIT / WAKE
6. Commitment
7. Policy version
8. Dependency invalidation
9. Selective revalidation
10. Side-effect idempotency
11. 3 ADK agents
12. Mission Control UI
13. Cloud deployment
14. OpenTelemetry trace

其他全部可以删。

---

# 28. 36-Hour Validation Gate

在正式投入大量开发之前，只验证一个问题：

能否实现：

```text
Decision D42
depends on Policy v12

Policy v12 → v13

Runtime automatically determines:

D42 stale
D43 unaffected
D44 downstream stale
```

然后：

```text
only affected branch reruns
```

如果这个 Demo 不够“哇”，不要继续。

因为这就是整个项目的灵魂。

---

# 29. Four-Minute Pitch

## 0:00–0:25

问题：

> Agents are becoming capable of performing work for minutes. Enterprises need them to perform work for weeks.

然后：

> But the world changes while an agent waits.

---

## 0:25–1:00

启动：

```text
Onboard Acme Analytics
```

三个 Agent 自动完成部分任务。

---

## 1:00–1:25

展示：

```text
Security Approved
```

及 Decision dependencies。

---

## 1:25–1:45

任务进入：

```text
WAITING
```

---

## 1:45–2:15

更新 Security Policy。

UI：

```text
POLICY DRIFT
```

过去 Decision 自动 stale。

---

## 2:15–2:45

Runtime selective rewind。

Security Agent 自动恢复。

其他已经完成的工作不重复。

---

## 2:45–3:15

新 evidence 到达。

Commitment 被触发。

Agent 自动继续。

---

## 3:15–3:35

任务完成。

---

## 3:35–3:50

kill worker → automatic recovery。

---

## 3:50–4:00

一句话：

> **Continuum doesn't just remember where an agent stopped. It remembers why it was allowed to continue.**

---

# 30. Final Positioning

不要宣传：

> Enterprise multi-agent platform.

也不要宣传：

> Durable agent workflow engine.

最终定位：

# Continuum

### The runtime that lets enterprise agents safely continue when the world has changed.

核心概念：

> **Semantic Continuity for Long-Lived Agents**

这是整个作品最值得押注的技术命题。