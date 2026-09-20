# Cover Letter — 慧图科技 · Agent 开发工程师（水利信息化）

> 投递岗位：Agent 开发工程师（水利信息化）
> 公司：慧图科技
> 期望薪资：20-30K

---

慧图科技 HR / 技术负责人 您好：

我是一名兼具**水利领域研究背景**与 **LLM Agent 工程落地经验**的算法工程师，从 BOSS 直聘看到贵司 Agent 开发工程师（水利信息化）岗位，深感匹配——我的研究方向正是水利领域的 AI 应用。

## 为什么我认为自己适合这个岗位

**1. 水利领域研究背景（硬核，非泛泛了解）**

我的学位论文方向是**洪水概率预报**（RL-RA-QR 模型），将强化学习与时序预测结合，实现多步滚动概率预报。在此过程中：
- 构建了完整的**多源时序特征融合管线**（降雨、径流、土壤湿度、历史水文数据），这与贵司"防汛抗旱、水资源调度"场景的多维数据融合需求高度同构
- 提出 **STM-SHAP** 可解释性方法（IEEE ISCTIS 2026 EI 一作），解决"哪些特征对预测影响最大"的问题——这正是水利智能决策中"为什么这么预测"的关键
- 熟悉概率预报、不确定性量化、滚动回测等时序预测全链路

**2. LLM Agent 工程落地（独立设计 + 全链路实现）**

我独立设计并实现了一套 **Multi-Agent Runtime**（基于 LangGraph），包含 6 个 Agent（Supervisor / Planner / Reviewer / Career / Research / Knowledge），完整覆盖：
- Agent 架构设计：BaseAgent → AgentRegistry → AgentExecutor，支持动态注册与调度
- RAG 系统：独立实现 Paper RAG 四件套（Embedder → VectorStore → Indexer → Retriever），支持语义检索与 section 过滤
- Prompt Engineering：为不同 Agent 设计专属 prompt，含 few-shot、输出格式约束、长短期记忆
- 任务调度：APScheduler + 4 通道提醒（Server酱/PushPlus），支持定时任务与异常恢复

**3. 技术栈完全匹配**

| JD 要求 | 我的经验 |
|---------|---------|
| Python + FastAPI + 异步编程 | FastAPI 全栈后端（14 个 Router，22 个端点） |
| LLM / Agent / Function Calling | Multi-Agent Runtime 6 个 Agent + LangGraph 图 |
| LangChain / RAG | LangGraph（LangChain 生态）+ 自研 RAG 四件套 |
| Prompt Engineering | 多 Agent prompt 设计 + 输出格式约束 + 记忆系统 |
| Docker + 私有化部署 | Docker Compose 编排（PostgreSQL + FastAPI + Next.js） |
| 智能问答 | PaperKnowledgeAgent（RAG 问答 + 知识库检索） |

## 关于水利信息化的理解

贵司深耕智慧水利 20 余年，从流域防洪到数字孪生——我认为水利行业正处在"规则驱动 → 数据驱动 → AI 驱动"的转型期，而 **Agent 是让 AI 真正嵌入业务流程的关键**：

- **防汛调度场景**：降雨/水位/流量的实时预测 + 多源数据融合 + 概率预报（不确定性量化）= 我的研究方向
- **文档智能场景**：防汛报告/工程档案/调度指令的结构化处理 + 信息抽取 + 语义检索 = 我的工程经验（招投标评审系统 3000+ 份文档）
- **智能决策场景**：Agent 调度 + RAG 知识检索 + 可解释性分析 = 我的 Agent 架构能力

## 一点补充

- 有一作 EI 会议论文（IEEE ISCTIS 2026，时序可解释性方向），可提供 DOI 验证
- 北航软件工程非全在读（2026-12 答辩），不影响全职工作
- 有 6 年+后端开发经验，熟悉 Python 生态与工程化部署

期待有机会进一步交流。感谢您的时间。

此致
敬礼

[姓名]
[电话] | [邮箱]
