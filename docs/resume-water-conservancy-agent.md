# [姓名] — 水利 AI Agent 工程师

> [电话] · [邮箱] · 北京
> 期望岗位：Agent 开发工程师（水利信息化 / 时序预测 / 智能决策）
> 期望薪资：20-30K

---

## 核心优势

- **水利领域研究背景**：学位论文方向为洪水概率预报（RL-RA-QR），一作 EI 会议论文（IEEE ISCTIS 2026）
- **LLM Agent 全链路**：独立设计 Multi-Agent Runtime（6 个 Agent + LangGraph），含 RAG、Prompt Engineering、任务调度
- **时序预测专家**：概率预报、多源特征融合、滚动回测、不确定性量化、可解释性分析（SHAP）
- **工程落地能力**：FastAPI + Python 全栈，Docker 部署，3000+ 份文档的文档智能系统

---

## 工作经历

### 东鉴科技（北京） · 算法工程师（Agent 应用方向）
*2026.01 – 2026.09*

**招投标智能评审系统**（全链路从 0 到 1）
- 设计并实现基于 LLM 的全链路自动评审系统，覆盖投标文档解析 → 报价抽取 → 废标条款审查
- 构建 cross-doc 跨文档检索引擎，实现条款级语义对齐（召回率 64.3% → 接入 Agent runtime 后提升至 >60% 弱项类目）
- 累计处理 **3000+ 份**非结构化投标文档，人工标注集评估驱动持续迭代
- 技术栈：Python / FastAPI / LangChain / RAG / Prompt Engineering

**Agent 智能体平台**（独立设计与实现）
- 设计 Multi-Agent Runtime 架构：BaseAgent → AgentRegistry → AgentExecutor，支持动态注册与调度
- 实现 6 个 Agent：Supervisor（意图路由）/ Planner（任务规划）/ Reviewer（结果评估）/ Career（职业分析）/ Research（研究计划）/ Knowledge（RAG 问答）
- 基于 LangGraph 构建 Agent 图流程，含条件路由与失败隔离（单 Agent 失败不中断整链）
- 自研 Paper RAG 四件套：Embedder → VectorStore → Indexer → Retriever，支持语义检索 + section 过滤

---

## 教育背景

### 北京航空航天大学 · 软件工程（非全日制硕士在读）
*预计 2026-12 答辩*

### 郑州航空工业管理学院 · 计算机科学与技术（本科）

---

## 科研成果

### 一作 EI 会议论文
**STM-SHAP: Exploring the Impact of Redundant and Lagged Features on Flood Forecasting**
- 会议：IEEE ISCTIS 2026（EI 检索）
- DOI：10.1109/ISCTIS70043.2026.11572181
- 核心贡献：提出 STM-SHAP 方法，用 SHAP 可解释性分析识别洪水预报中的冗余与滞后特征，解决"哪些特征真正有用"的问题
- 意义：**时序预测的可解释性 = 水利智能决策的关键需求**（为什么这么预测、哪些因素影响最大）

### 学位论文（在研）
**RL-RA-QR：基于强化学习的洪水概率预报**
- 核心方法：强化学习 + 分位数回归，实现多步滚动概率预报与置信区间输出
- 数据：多流域水文数据（降雨、径流、土壤湿度、历史水文）
- 验证：多流域对比实验，q99 分位数预报显著优于基准方法
- **与水利行业的关联**：洪水预报 = 流域防洪的核心技术支撑，概率预报 = 不确定性下的决策依据

---

## 技能清单

| 类别 | 技能 | 等级 |
|------|------|------|
| **AI Agent** | LangGraph / Multi-Agent 架构 / Prompt Engineering / Function Calling | ★★★★★ |
| **RAG** | 语义检索 / 向量存储 / 文档分块 / 跨文档对齐 | ★★★★★ |
| **时序预测** | 概率预报 / 多源特征融合 / 滚动回测 / 不确定性量化 | ★★★★★ |
| **可解释性** | SHAP / 特征归因 / 冗余/滞后特征识别 | ★★★★☆ |
| **Python** | FastAPI / 异步编程 / SQLAlchemy / PyTorch | ★★★★☆ |
| **NLP** | 信息抽取 / 文本分类 / 实体关系抽取 / 文档结构化 | ★★★★☆ |
| **工程化** | Docker / Linux / Git / CI/CD / 私有化部署 | ★★★☆☆ |
| **数据库** | PostgreSQL / SQLite / ChromaDB（向量库） | ★★★☆☆ |

---

## 项目亮点

### 洪水概率预报系统（RL-RA-QR）
- **问题**：传统确定性预报无法量化不确定性，决策者无法评估风险
- **方案**：强化学习指导分位数回归，输出概率分布而非单点预测
- **结果**：多流域对比中概率预报显著优于基准；q99 分位数预报为极端事件提供风险量化
- **技术**：PyTorch / 时序特征融合 / 滚动回测 / 概率评估指标

### 招投标智能评审系统
- **问题**：3000+ 份/季度投标文档人工审查，废标条款散落，效率低且易漏
- **方案**：LLM Agent 全链路自动评审（文档解析 → 条款抽取 → 废标审查）
- **结果**：覆盖率 56% → 90%（Agent ReAct），单份审查时间 30min → 10min
- **技术**：FastAPI / LangChain / RAG / 跨文档检索 / Prompt v3

### Multi-Agent Runtime 平台
- **问题**：单一 Agent 无法处理复杂多步骤任务
- **方案**：Supervisor 意图路由 → 多 Agent 协作 → Reviewer 结果评估
- **结果**：6 个 Agent 协同工作，含失败隔离与可观测性（AgentRun 追踪）
- **技术**：LangGraph / BaseAgent 框架 / AgentRegistry / 条件路由

---

## 自我评价

水利行业正从"规则驱动"向"AI 驱动"转型，**Agent 是让 AI 嵌入业务流程的关键**。我的优势在于：

1. **水利研究背景**不是"了解水利"，而是**做过洪水预报并发表论文**——理解时序预测、多源数据融合、不确定性量化的核心挑战
2. **Agent 工程能力**不是"用过框架"，而是**独立设计并实现了 6 个 Agent 的全链路系统**——从架构设计到 RAG 到任务调度到可观测性
3. **可解释性**是水利智能决策的刚需——"为什么这么预测"比"预测结果是什么"更重要，这是我的论文核心贡献
