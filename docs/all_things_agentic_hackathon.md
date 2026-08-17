# All Things Agentic Hackathon 赛事指南

> **官方页面**: [All Things Agentic Hackathon (Devpost)](https://allthingsagentichackathon.devpost.com/)
> **主办方**: Google Cloud & Devpost
> **核心主题**: 构建下一代自主式 AI Agent（超越单轮/多轮简单问答，具备异步后台执行、多步骤规划、工具调用、长期记忆与复杂工作流自动化能力）。

---

## 1. 关键时间节点 (Timeline)

| 事项 | 时间 (PT / UTC) | 北京时间 (UTC+8) |
| :--- | :--- | :--- |
| **报名 & 提交开放** | 2026-08-04 10:45 EDT | 2026-08-04 22:45 |
| **$150 云额度申领截止** | 2026-08-28 12:00 PDT | 2026-08-29 03:00 |
| **作品提交截止 (Deadline)** | **2026-08-31 17:00 PDT** | **2026-09-01 08:00** |
| **评审期** | 2026-09-01 至 2026-10-01 | - |
| **公布获奖结果** | 2026-10-08 10:00 PDT 左右 | 2026-10-09 01:00 |

---

## 2. 参赛赛道 (Tracks)

参赛项目必须选择归属于以下三个赛道之一：

### 赛道一：The Taskmaster（任务大师）
* **核心定位**: 事件驱动与自主工作流执行（Event-driven workflow & autonomous routing）。
* **要求**: 不只是文本生成，必须具备真实行动力（Action-taking）。解决日常工作/学习/生活中繁琐、多步骤的痛点（"Bring Your Own Friction"）。
* **典型示例**:
  * 自动项目经理：监听会议录音/文本 -> 自动提取 Action Items -> 调用 Jira 创建任务 -> 同步 Slack。
  * 自由职业自动化管道：监控收件箱 -> 识别询价 -> 查询日历可用性 -> 基于过往案例起草提案草稿并提示审核。

### 赛道二：The Collaborative Partner（协同伙伴）
* **核心定位**: 有状态的多轮深度互动与自适应学习（Stateful, multi-turn dialogue with RAG & persistent memory）。
* **要求**: Agent 主动引导用户、收集反馈并形成记忆，根据历史交互持续自适应与个性化，而非每次重新开始。
* **典型示例**:
  * 法律/技术复杂文档导读伴侣：逐段解读、主动提问考核、记录用户薄弱概念并在后续解释中动态调整。
  * 交互式 UI/UX 设计助理：将模糊构想转化为原型线框，并通过用户修正逐步学习品牌规范。

### 赛道三：The Fortified Enterprise Fleet（企业级智能体集群）
* **核心定位**: 企业级多 Agent 大规模编排、长生命周期治理与零信任安全。
* **要求**: 解决跨部门智能体发现、跨会话长期状态保持（Weeks-long context）、数据合规与安全防护。
* **推荐技术组件 (Gemini Enterprise Agent Platform)**:
  * **Agent Registry**: 企业级智能体与工具的注册、发现与版本管理。
  * **Agent Runtime + Memory Bank**: 长生命周期异步运行环境与跨会话持久化记忆库。
  * **Agent Identity + Agent Gateway**: 零信任权限控制、统一路由与安全策略下发。
  * **Model Armor**: 提示词注入拦截、工具投毒防护、PII 隐私防泄露护栏。
  * **Agent Observability**: 符合 OpenTelemetry 的审计日志与推理链追踪。

---

## 3. 强制技术栈要求 (Mandatory Tech Stack)

参赛项目**必须同时满足**以下三项条件：

1. **大模型层**:
   * 使用 **Gemini 3.5**（或更新版本）。
   * 接入方式需通过 **Gemini API** 或 **Google Cloud Vertex AI**。
2. **Agent 框架层（至少选一）**:
   * **Google ADK (Agent Development Kit)**: [github.com/google/adk-python](https://github.com/google/adk-python) / [adk-docs](https://google.github.io/adk-docs)
   * **Antigravity SDK**: [antigravity.google/docs/sdk](https://antigravity.google/docs/sdk)
   * **GenAI SDK**
   * **Genkit**: [firebase.google.com/docs/genkit](https://firebase.google.com/docs/genkit)
3. **云基础设施层（至少选一）**:
   * 必须使用 Google Cloud 托管服务（如 **Cloud Run**, **Cloud SQL**, **Firestore**, **GKE**, **Pub/Sub** 等）。

---

## 4. 奖项设置与奖金池 (Prizes)

总奖池超过 **$180,000 USD**（包含现金及 Google Cloud Credits）：

| 奖项 | 名额 | 现金奖励 | 云额度奖励 | 其他权益 |
| :--- | :---: | :---: | :---: | :--- |
| **Grand Prize（总冠军）** | 1 | **$50,000** | $5,000 | Google 团队 1v1 交流 + 官方社媒宣发 |
| **The Taskmaster Track 冠军** | 1 | **$20,000** | $2,000 | Google 团队 1v1 交流 + 官方宣发 |
| **The Collaborative Partner Track 冠军** | 1 | **$20,000** | $2,000 | Google 团队 1v1 交流 + 官方宣发 |
| **The Fortified Enterprise Fleet Track 冠军** | 1 | **$20,000** | $2,000 | Google 团队 1v1 交流 + 官方宣发 |
| **Startup Excellence（初创奖）** | 1 | **$20,000** | $5,000 | 需企业主体报名并提供企业邮箱 |
| **Individual / Hobbyist（最佳个人/小队）** | 2 | **$10,000** | $1,000 | 个人或业余团队均可参评 |
| **Best Architectural Design（最佳架构）** | 2 | **$5,000** | $1,000 | 架构设计最高分项目 |
| **Best Multimodal UX（最佳多模态体验）** | 2 | **$5,000** | $1,000 | 多模态交互最高分项目 |
| **Honorable Mentions（优胜提名）** | 5 | **$2,000** | $500 | 综合排名前列候补项目 |

---

## 5. 评审标准 (Judging Criteria)

最终得分由 **基础分 (1-5 分)** 与 **加分项 (最多 +1.0 分)** 构成，满分 6 分。

### 基础评审维度 (Stage Two: 1-5分)
1. **创新性与实用价值 (Innovation & Operational Utility - 40%)**
   * 解决的是否为真实场景痛点？
   * 是否体现出高度自主执行能力（而不是问答型机器人）？
2. **架构严谨度与技术选型 (Architectural Discipline & Tech Stack - 30%)**
   * 系统的模块化解耦程度、状态管理与持久化设计。
   * 容错与恢复机制（如 Agent 死循环、幻觉容错）。
3. **Demo 与生产就绪度 (Demo & Production Readiness - 30%)**
   * 演示视频是否展示了 live 未剪辑的实际动作执行。
   * 仓库文档与本地/云端部署说明是否清晰完整、可复现。
   * 是否证明了后端在 Google Cloud 上稳定运行。

### 额外加分项 (Stage Three: 最高 +1.0分)
* **发布技术内容 (+0.2)**: 在 Medium、Dev.to 或 YouTube 上公开发布技术解析文章/视频（需注明为参赛作品制作）。
* **社媒传播 (+0.2)**: 在 X/LinkedIn/Instagram 发布项目动态并带上标签 `#AllThingsAgenticHackathon`。
* **集成额外 Google AI 模型 (最高 +0.6)**: 成功集成如 Gemma、Veo、Lyria 等模型（每个 +0.2 分）。

---

## 6. 作品提交清单 (Submission Checklist)

1. [ ] **选择赛道**: 明确归属于 Taskmaster / Collaborative Partner / Fortified Enterprise Fleet 之一。
2. [ ] **演示视频 (Demo Video)**:
   * 时长 **≤ 4 分钟**，公开发布于 YouTube 或 Vimeo。
   * 必须包含：问题陈述、价值主张、Live 运行演示。
   * **必须证明后端运行于 Google Cloud**（如 Cloud Run 控制台、Vertex AI 日志或 `.run.app` 域名）。
   * 英文或包含英文字幕。
3. [ ] **代码仓库 (Code Repository)**:
   * GitHub / GitLab / Bitbucket 链接。若为私有仓库，需添加 `testing@devpost.com` 与 `cloudhackathons@google.com` 为协作者。
   * 根目录需包含详细的 `README.md`，提供完整的本地运行与云端部署步骤（Spin-up Instructions）。
4. [ ] **系统架构图 (Architecture Diagram)**:
   * 视觉化呈现 Gemini、Agent 框架、数据库、云服务及各组件通信链路。
5. [ ] **文字说明 (Text Description)**:
   * 项目背景、功能亮点、使用的技术栈、数据源说明以及开发心得。
6. [ ] **线上可体验地址 (Hosted URL)**:
   * 建议提供可直接访问的 Web UI / 插件 / 体验入口（如有鉴权需提供测试账号）。

---

## 7. 实用官方资源与链接

* **$150 云额度申请表**: [Google Form 申领链接](https://forms.gle/riGhgDSHkHeMx8Ca6)
* **GEAR 学习计划 (免费沙箱与徽章)**: [Google Developer GEAR](https://developers.google.com/program/gear)
* **Google ADK Python 仓库**: [github.com/google/adk-python](https://github.com/google/adk-python)
* **Gemini Enterprise Agent Platform 文档**: [docs.cloud.google.com/gemini-enterprise-agent-platform](https://docs.cloud.google.com/gemini-enterprise-agent-platform)
