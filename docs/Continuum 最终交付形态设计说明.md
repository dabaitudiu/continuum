# Continuum 最终交付形态设计说明

## 1. 最终交付的不是 SDK，而是一个可运行产品

Continuum 最终应交付为一个：

> **面向长期运行企业 Agent 的 Mission Control + Runtime。**

评委打开后看到的不是 CLI、YAML 或 Python package，而是一个可以直接操作的 Web 产品。

它需要能够展示：

- 一个长期 Agent Mission 当前执行到哪里；
- 哪些 Agent 正在运行、等待或阻塞；
- 某个 Decision 当初为什么成立；
- 某个 Policy / Permission / Evidence 改变后，哪些 Decision 已失效；
- Runtime 如何只重新执行受影响的部分；
- 外部事件到达后 Agent 如何自动恢复；
- 已产生的 side effect 如何避免重复执行；
- 整个执行过程如何被完整审计。

---

# 2. 产品形态

暂定产品名：

# Continuum

副标题：

> **Mission Control for Long-Lived AI Agents**

或者：

> **The runtime that lets enterprise agents safely continue when the world has changed.**

整体产品可以理解成：

> Temporal + Agent Observability + Decision Provenance + Memory Bank

但专门服务于**持续数天乃至数周的 AI Agent**。

---

# 3. 核心用户体验

用户进入 Continuum 后，可以创建一个长期任务：

```text
New Mission

Onboard Acme Analytics as a new enterprise vendor.
```

系统随后真正启动一组 Gemini + Google ADK Agent。

例如：

```text
Vendor Agent
Security Agent
Procurement Agent
```

它们自动执行：

```text
收集资料
→ 安全审核
→ 商务审核
→ 等待外部审批
→ 接收新事件
→ 恢复执行
→ 完成 Vendor Onboarding
```

整个过程中，Continuum Runtime 持久化：

```text
State
Decision
Evidence
Dependency
Commitment
Side Effect
Policy Version
Identity Context
```

---

# 4. 主界面：Mission Control

Mission Control 是产品最重要的页面。

示意：

```text
┌────────────────────────────────────────────────────┐
│ Continuum                              Runs  Agents │
├────────────────────────────────────────────────────┤
│ Vendor Onboarding #ACME-042                        │
│                                                    │
│ STATUS: REVALIDATING                               │
│                                                    │
│ Timeline                                           │
│ ● Vendor submitted documents                      │
│ ● Security review passed                          │
│ ● Waiting for procurement approval                │
│ ⚠ Security policy v12 → v13                       │
│ ⚠ Security decision became stale                  │
│ ● Security agent resumed                          │
│                                                    │
│ Agent Fleet                                        │
│ Vendor Agent       WAITING                        │
│ Security Agent     RUNNING                        │
│ Procurement Agent  BLOCKED                        │
└────────────────────────────────────────────────────┘
```

用户应该能够在一个页面内回答：

> 这个任务现在发生了什么？

---

# 5. 产品核心 Demo

整个产品最重要的演示并不是“Agent 成功完成任务”。

而是：

> **Agent 等待期间，现实世界改变了。**

例如 Security Agent 已经得到：

```text
SECURITY APPROVED
```

该 Decision 当时依赖：

```text
Security Policy v12
SOC2 Report A31
Vendor Profile r7
```

任务随后进入等待状态：

```text
WAITING FOR PROCUREMENT APPROVAL
```

此时人为触发：

```text
Security Policy v12 → v13
```

新政策要求所有处理 Customer PII 的 AI Vendor 提供 Penetration Test。

Continuum 立即检测：

```text
POLICY DRIFT DETECTED
```

并自动计算：

```text
Security Decision #42       STALE
Procurement Approval        STALE
Vendor Activation           BLOCKED
```

但同时：

```text
Financial Review            VALID
Identity Verification       VALID
```

因此系统不会从头执行整个 Mission。

只重新执行真正受到影响的部分。

这应该成为整个产品最主要的：

# Aha Moment

---

# 6. Decision Graph

Decision Graph 是 Continuum 最重要的视觉资产之一。

它负责展示：

```text
Evidence
   ↓
Decision
   ↓
Derived Decision
   ↓
Action
```

例如：

```text
Security Policy v12  ✕
         │
         ▼
Security Decision #42
         │
         ▼
Procurement Approval
         │
         ▼
Vendor Activation
```

Policy 更新以后：

```text
Security Decision #42     STALE
Procurement Approval      STALE
Vendor Activation         BLOCKED
```

而其他没有依赖这个 Policy 的 branch 保持：

```text
VALID
```

这个页面必须让评委不需要听解释，就能理解：

> **Continuum 知道一个旧 Decision 为什么已经不能再被信任。**

---

# 7. 产品需要的五个主要页面

最终不需要做一个庞大的 Enterprise Platform。

建议控制在五个核心页面。

## 7.1 Runs / Missions

显示所有长期运行任务：

```text
Vendor Onboarding — WAITING
Security Audit — RUNNING
Procurement Review — REVALIDATING
Customer Migration — BLOCKED
```

展示：

- 当前状态
- 已运行时间
- 等待事件
- Agent 数量
- 最近一次状态变化

---

## 7.2 Mission Control

某一个 Mission 的主要控制台。

展示：

- Timeline
- 当前状态
- Agent Fleet
- Pending Commitments
- Policy Drift
- External Events
- Current Blockers

这是默认进入页面。

---

## 7.3 Decision Graph

展示：

```text
Evidence
Decision
Dependency
Action
```

并支持：

- VALID
- STALE
- REVALIDATING
- INVALID
- BLOCKED

等状态可视化。

---

## 7.4 Memory & Commitments

不重点展示普通聊天记忆。

而展示长期 Agent 真正重要的 Memory：

### Working State

当前 workflow 状态。

### Decision Memory

以前做过什么决定，为什么。

### Artifact Memory

当时用了哪些真实材料。

### Commitment Memory

Agent 未来仍然欠什么事情。

例如：

```text
WAITING

Penetration Test
Expected from: Acme Analytics
Trigger: VendorDocumentUploaded
Resume: Security Review
```

---

## 7.5 Audit / Trace

展示：

```text
Agent
Tool
Identity
Arguments
Policy Version
Timestamp
Result
Side Effect
```

例如：

```text
Security Agent

Tool:
read_vendor_document

Identity:
security-agent@continuum

Policy:
security-policy:v13

Result:
SUCCESS
```

并能够进一步关联 OpenTelemetry Trace。

---

# 8. Agent Fleet

最终 Demo 使用三个 Agent 即可。

不要为了体现 Fleet 而制造十几个 Agent。

## Vendor Agent

负责：

```text
vendor profile
documents
vendor communication
```

## Security Agent

负责：

```text
security policy
security evidence
risk review
```

## Procurement Agent

负责：

```text
commercial approval
vendor activation
```

Google ADK 负责 Agent 本身的：

- reasoning；
- tool use；
- delegation。

Continuum 则负责它们跨时间执行时的：

- state；
- decisions；
- dependencies；
- commitments；
- recovery；
- revalidation。

---

# 9. 模拟企业环境

不需要真正接一家企业的生产系统。

项目中应内置一个：

# Enterprise Simulator

用于制造完整、真实的 side effect。

包含：

```text
Vendor Database
Security Policy Store
Procurement System
Document Upload Service
Email Simulator
Approval Simulator
```

例如 Agent 真正执行：

```text
vendors/acme.status

PENDING
    ↓
ACTIVE
```

而不是只输出：

> “I have activated the vendor.”

这样才能证明 Agent：

> **真的采取了 Action。**

---

# 10. Long-Time Compression

现实里的长期 Agent 可能需要等待七天。

比赛 Demo 显然不能真的等七天。

因此产品需要内置：

```text
Simulate Time
```

例如：

```text
Simulate: 7 days later
```

然后生成：

```text
VendorDocumentUploaded
```

事件。

Runtime 收到 Pub/Sub Event 后：

```text
match Commitment
↓
wake Agent
↓
restore state
↓
revalidate dependencies
↓
continue execution
```

这既保留长期 Agent 的语义，又能让完整流程在几分钟内展示。

---

# 11. Crash Recovery Demo

为了证明 Continuum 不是一套前端动画，可以加入一个非常直观的操作：

```text
Kill Worker
```

执行过程中：

```text
WORKER LOST
```

然后：

```text
NEW WORKER STARTED

RUN RECOVERED
```

Runtime 从持久化状态恢复。

同时：

```text
Side Effect Ledger

vendor_email_sent = COMMITTED
```

所以恢复后不会发送第二封相同邮件。

这个 Demo 可以很好地证明：

> Runtime 是真实存在的，而不是 UI 上伪造出来的状态。

---

# 12. 技术架构

总体架构：

```text
                     Web Console
                          │
                          ▼
                     Cloud Run
                          │
                  Continuum Runtime
                          │
        ┌─────────────────┼─────────────────┐
        │                 │                 │
        ▼                 ▼                 ▼
   Google ADK        State Engine       Agent Gateway
        │                 │                 │
        ▼                 ▼                 ▼
   Gemini 3.5         Firestore         Tool APIs
        │
   ┌────┼────┐
   │    │    │
Vendor Security Procurement
Agent   Agent   Agent


                    Pub/Sub
                       │
           Async Events / Wakeups
                       │
                Continuum Runtime


                    Firestore
                       │
          ┌────────────┼────────────┐
          │            │            │
        Runs       Decisions     Evidence
        State      Dependencies  Commitments


                OpenTelemetry
                       │
                 Cloud Trace
```

---

# 13. Repo 形态

最终应交付一个清晰、可复现的完整 repository：

```text
continuum/
├── frontend/
│   └── Mission Control UI
│
├── runtime/
│   ├── state machine
│   ├── resume
│   ├── invalidation
│   └── revalidation
│
├── agents/
│   ├── vendor/
│   ├── security/
│   └── procurement/
│
├── gateway/
│   ├── identity
│   ├── policy
│   └── idempotency
│
├── state/
│   ├── decisions
│   ├── evidence
│   ├── commitments
│   └── side-effects
│
├── simulator/
│   ├── vendor-db
│   ├── policy-store
│   ├── procurement
│   └── documents
│
├── infra/
│   └── Google Cloud deployment
│
├── docs/
│   └── architecture
│
└── README.md
```

---

# 14. 最终比赛交付物

比赛真正提交的内容分成两层。

## 第一层：产品

一个部署在 Google Cloud 上的：

# Continuum Web App

评委可以：

```text
打开网页
↓
启动 Demo Scenario
↓
看到 Agent 开始执行
↓
注入 Policy Change
↓
观察 Decision invalidation
↓
模拟新 Evidence 到达
↓
看到 Agent 自动恢复
↓
看到 Mission 完成
```

---

## 第二层：Submission Package

包含：

### Hosted Project URL

Continuum Web App。

### Source Repository

完整 GitHub Repository。

### README

包括：

- 系统介绍
- 技术栈
- 本地启动方法
- Google Cloud 部署方法
- Demo 操作方法

### Architecture Diagram

清楚展示：

```text
Gemini
ADK
Cloud Run
Firestore
Pub/Sub
Agents
Runtime
Gateway
Observability
```

### Demo Video

不超过 4 分钟。

### Devpost Write-up

包括：

- Problem
- Value Proposition
- Architecture
- Features
- Technologies
- Findings & Learnings

---

# 15. Demo Mode

为了让评委能够自己体验，产品首页建议直接提供：

# Run Demo Scenario

而不是要求用户自己配置一个企业流程。

点击后自动创建：

```text
Vendor Onboarding — Acme Analytics
```

整个 Demo 可以按以下流程运行：

```text
Mission Created
↓
Vendor Agent starts
↓
Security Agent reviews documents
↓
Security Decision APPROVED
↓
Workflow enters WAITING
↓
Inject Policy Change
↓
POLICY DRIFT DETECTED
↓
Old Decision STALE
↓
Affected branch invalidated
↓
Security Agent resumes
↓
Missing Pen Test identified
↓
Commitment created
↓
Simulate 7 days later
↓
Pen Test arrives
↓
Commitment triggered
↓
Security Review passes
↓
Procurement resumes
↓
Vendor ACTIVE
```

整个流程控制在 2～3 分钟。

---

# 16. 明确不做什么

最终产品不能因为“Enterprise Fleet”几个字而无限膨胀。

不做：

- 通用 workflow builder；
- drag-and-drop Agent builder；
- Agent marketplace；
- 通用 IAM；
- Kubernetes 替代品；
- Temporal 替代品；
- 通用 vector memory platform；
- Zapier 替代品；
- 完整企业审批平台。

Fleet 的其他能力只做到足够支持核心故事即可。

核心永远是：

> **Long-lived Agent Execution + Semantic Continuity**

---

# 17. 产品与 Runtime 的关系

Continuum 应同时具备两层。

## Product Layer

评委看到：

```text
Mission Control
Decision Graph
Commitment Memory
Policy Drift
Audit Trail
```

## Runtime Layer

背后实际运行：

```text
Durable State
Semantic Resume
Decision Dependency
Selective Revalidation
Commitment Wakeup
Side-Effect Safety
```

二者缺一不可。

只有 Product：

> 容易变成漂亮 Demo。

只有 Runtime：

> 容易变成基础设施作业。

必须做到：

> **前端把真正存在的 Runtime semantics 清晰可视化。**

---

# 18. 最终产品的一句话定义

Continuum 最终不是：

> 一个 Agent Framework。

不是：

> 一个 Agent Memory Database。

也不是：

> 一个 Durable Workflow Engine。

而是：

# 一个让长期运行的企业 Agent 在世界已经发生变化之后，仍然能够安全继续工作的 Runtime 与 Mission Control。

最核心的用户可见能力是：

> **它不只记得 Agent 在哪里停下。**

> **它还知道 Agent 当初为什么能够继续，以及现在这些理由是否仍然成立。**

最终 Pitch：

> **Continuum doesn't just remember where an agent stopped. It remembers why it was allowed to continue.**