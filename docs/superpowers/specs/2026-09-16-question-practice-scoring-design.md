# 题库练习与评分系统设计

> 日期：2026-09-16
> 状态：已批准
> 前置依赖：题库已建成（95 题，4 分类），skill_name 已关联，coverage matrix 已有

## 1. 背景与目标

**现状问题**：题库练习只有"标记已练习"按钮（hit_count +1），用户无法真正答题，看不到对错反馈，无法衡量掌握程度。

**目标**：
- 支持 4 种题型（选择/判断/填空/开放）的答题体验
- LLM 自动评分，即时反馈对错和得分
- 持久化练习记录，生成技能×正确率统计
- 与现有题库覆盖率矩阵联动（从"有没有题"升级为"练没练过、练得怎么样"）

## 2. 题型定义

| 题型 key | 说明 | 来源 |
|---|---|---|
| `open` | 开放问答（现有主力） | 直接用 question + answer_outline |
| `choice` | 单选题（4 选 1） | LLM 从 answer_outline 生成 4 选项 + 正确答案 |
| `fill` | 填空题 | LLM 从 answer_outline 提取关键术语挖空 |
| `judge` | 判断题（对/错） | LLM 从 answer_outline 生成陈述 + 正误标记 |

**混合模式**：默认 LLM 动态生成题型；如果题目手动配了 `options`（JSON 字段），则用原版不覆盖。

**小测验默认分配**（10 题）：选择 3 + 判断 3 + 填空 2 + 开放 2。比例可配。

## 3. 数据模型变更

### 3.1 `interview_questions` 表新增字段

```sql
ALTER TABLE interview_questions ADD COLUMN question_type VARCHAR(20) DEFAULT 'open';
ALTER TABLE interview_questions ADD COLUMN options TEXT;  -- JSON: {"choices": ["A","B","C","D"], "correct": "B"} 或 null
```

- `question_type`：默认 `open`，手动可改为 `choice`/`fill`/`judge`
- `options`：仅 `choice` 类型有值，JSON 格式 `{"choices": [...], "correct": "B"}`

### 3.2 新建 `practice_records` 表

```sql
CREATE TABLE practice_records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    question_id INTEGER NOT NULL REFERENCES interview_questions(id),
    question_type VARCHAR(20) NOT NULL,       -- 本次实际题型
    user_answer TEXT NOT NULL,                -- 用户答案
    correct_answer TEXT,                      -- 正确答案
    correct BOOLEAN NOT NULL DEFAULT 0,       -- 是否正确
    score INTEGER NOT NULL DEFAULT 0,         -- 0-100
    feedback TEXT,                            -- LLM 反馈说明
    outline_covered TEXT,                     -- JSON string[]: 覆盖了哪些要点
    outline_missed TEXT,                      -- JSON string[]: 缺了哪些要点
    skill_name VARCHAR(100),                  -- 关联技能
    mode VARCHAR(20) DEFAULT 'single',        -- single | quiz
    session_id VARCHAR(50),                   -- 小测验 session（同一套题共享）
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);
```

## 4. API 设计

### 4.1 答题：`POST /api/interview/practice`

```json
// 请求
{
  "question_id": 24,
  "question_type": "choice",
  "user_answer": "B",
  "generated_options": ["A", "B", "C", "D"],
  "skill_name": "LoRA/QLoRA",
  "mode": "single"
}

// 响应
{
  "correct": true,
  "score": 85,
  "max_score": 100,
  "feedback": "正确。LoRA 通过低秩分解冻结原始权重...",
  "correct_answer": "B",
  "outline_covered": ["核心思路", "参数效率"],
  "outline_missed": ["与全量微调对比"],
  "record_id": 142
}
```

**评分逻辑**（LLM 驱动，一次答题 = 一次 LLM call）：

| 题型 | 评分策略 |
|---|---|
| `choice` | 选项匹配 + 语义解释 |
| `judge` | 布尔匹配 + 解释 |
| `fill` | 语义等价判断（LLM 判断用户答案与参考答案是否等价） |
| `open` | 按 answer_outline 逐条比对覆盖率，0-100 分 |

**副作用**：
- `interview_questions.hit_count` +1
- 如果 score ≥ 80 且 `is_verified=false`，自动标记 `is_verified=true`

### 4.2 小测验：`POST /api/interview/quiz/start`

```json
// 请求
{
  "skill_name": "Transformer",   // 可选
  "category": "LLM",             // 可选
  "count": 10                    // 默认 10
}

// 响应
{
  "session_id": "quiz_abc123",
  "questions": [
    {
      "id": 24,
      "question": "LoRA 的核心思路是什么？",
      "question_type": "choice",
      "options": ["A. 全量微调", "B. 低秩分解", "C. 知识蒸馏", "D. 剪枝"],
      "skill_name": "LoRA/QLoRA",
      "difficulty": "intermediate"
    }
  ],
  "count": 10
}
```

- 从题库 pick_questions 筛选，对每道题 LLM 生成对应题型
- 手动配了 options 的题直接返回原版
- session_id 用于关联同一套测验的所有答题记录

### 4.3 测验结果：`GET /api/interview/quiz/{session_id}/result`

```json
{
  "session_id": "quiz_abc123",
  "total_score": 72,
  "count": 10,
  "correct_count": 7,
  "by_type": {
    "choice": {"count": 3, "correct": 3, "avg_score": 95},
    "judge":  {"count": 3, "correct": 2, "avg_score": 70},
    "fill":   {"count": 2, "correct": 1, "avg_score": 55},
    "open":   {"count": 2, "correct": 1, "avg_score": 45}
  },
  "weak_skills": ["Transformer"],
  "records": [
    {
      "question_id": 24,
      "question_type": "choice",
      "question": "LoRA 的核心思路是什么？",
      "user_answer": "B",
      "correct_answer": "B",
      "correct": true,
      "score": 100,
      "feedback": "正确。LoRA 通过低秩分解..."
    }
  ]
}
```

### 4.4 练习统计：`GET /api/interview/practice/stats`

```json
{
  "total_practiced": 47,
  "total_correct": 32,
  "accuracy": 68.1,
  "by_type": {
    "choice":  {"practiced": 20, "correct": 16, "accuracy": 80.0},
    "judge":   {"practiced": 12, "correct": 10, "accuracy": 83.3},
    "fill":    {"practiced": 8,  "correct": 4,  "accuracy": 50.0},
    "open":    {"practiced": 7,  "correct": 2,  "accuracy": 28.6}
  },
  "by_skill": [
    {"skill": "LoRA/QLoRA",  "practiced": 10, "correct": 8, "accuracy": 80.0},
    {"skill": "Transformer", "practiced": 8,  "correct": 3, "accuracy": 37.5}
  ],
  "weak_skills": ["Transformer", "RLHF"],
  "weak_types": ["open"],
  "recent_sessions": [
    {"session_id": "abc123", "date": "2026-09-16", "score": 72, "count": 10}
  ]
}
```

## 5. 前端设计

### 5.1 新增组件

| 组件 | 文件 | 用途 |
|---|---|---|
| `QuestionCard` | `components/QuestionCard.tsx` | 答题卡片容器，根据 question_type 切换子组件 |
| `ChoiceQuestion` | `components/questions/ChoiceQuestion.tsx` | 4 选 1 Radio 组 |
| `JudgeQuestion` | `components/questions/JudgeQuestion.tsx` | 对/错 Toggle |
| `FillQuestion` | `components/questions/FillQuestion.tsx` | 文本输入框 |
| `OpenQuestion` | `components/questions/OpenQuestion.tsx` | 多行文本 + 参考答案展开 |
| `ResultCard` | `components/ResultCard.tsx` | 答题结果（分数、反馈、正确答案） |
| `QuizSummary` | `components/QuizSummary.tsx` | 测验总结（总分、题型柱状图、薄弱技能） |
| `PracticeStats` | `components/PracticeStats.tsx` | 练习统计面板（正确率、题型分布、薄弱点） |

### 5.2 现有组件改动

- `QuestionBoard.tsx`：每行加「练习」按钮（替代现有「标记练习」），点击打开 QuestionCard 弹窗
- 新增 `/questions/practice` 页面：小测验入口 + PracticeStats 统计面板

### 5.3 前端服务层

```typescript
// interviewService.ts 新增

interface PracticeResult {
  correct: boolean;
  score: number;
  maxScore: number;
  feedback: string;
  correctAnswer: string;
  outlineCovered: string[];
  outlineMissed: string[];
  recordId: number;
}

interface QuizStart {
  sessionId: string;
  questions: QuizQuestion[];
  count: number;
}

interface QuizQuestion {
  id: number;
  question: string;
  questionType: QuestionType;
  options: string[] | null;
  skillName: string | null;
  difficulty: string;
}

// 答题
postPractice(payload): Promise<PracticeResult>

// 开始测验
startQuiz(payload): Promise<QuizStart>

// 测验结果
getQuizResult(sessionId): Promise<QuizResult>

// 练习统计
getPracticeStats(): Promise<PracticeStats>
```

### 5.4 用户交互流程

**单题练习**：
```
题库列表 → 点击「练习」→ 弹出 QuestionCard（按题型渲染）
→ 作答 → 提交 → 显示 ResultCard（分数+反馈）→ 「下一题」/「关闭」
```

**小测验**：
```
题库页 → 点击「开始测验」→ 选范围（技能/分类/JD 推荐）
→ 进入测验（进度条 1/10）→ 逐题作答 → QuizSummary 总结页
```

## 6. LLM Prompt 策略

### 6.1 题型生成 Prompt

```
你是一位 AI 面试出题专家。根据以下面试题和参考答案，生成一道{题型}。

题目：{question}
参考答案要点：{answer_outline}

要求：
- choice：生成 4 个选项（A/B/C/D），其中 1 个正确（来自 answer_outline），3 个有迷惑性但可排除
- judge：生成一个陈述句，50% 概率正确（直接来自要点），50% 概率错误（轻微篡改关键细节）
- fill：从 answer_outline 中选 1-2 个关键术语挖空，生成题目文本

输出 JSON：{"question": "...", "correct_answer": "...", "options": [...]}
```

### 6.2 评分 Prompt

```
你是一位面试评分专家。评判用户对面试题的回答。

题目：{question}
参考答案要点：{answer_outline}
用户答案：{user_answer}

评分标准：
- 选择/判断题：答案正确得 100 分，错误得 0 分
- 填空题：语义等价得 100 分，部分相关得 50 分，错误得 0 分
- 开放题：按要点覆盖率评分（覆盖 N/M 个要点 → N/M * 100）

输出 JSON：
{
  "correct": true/false,
  "score": 0-100,
  "feedback": "一句话解释",
  "outline_covered": ["要点1", "要点2"],
  "outline_missed": ["要点3"]
}
```

## 7. 实现分批

### P0：核心答题能力（最小可用）
- 新建 `practice_records` 表（migration）
- `POST /api/interview/practice` 答题 + LLM 评分
- 前端 QuestionCard + 4 种题型组件 + ResultCard
- QuestionBoard 替换「标记练习」为「练习」按钮

### P1：小测验模式
- `POST /api/interview/quiz/start` 出题
- `GET /api/interview/quiz/{session_id}/result` 结果
- 前端测验流程页 + QuizSummary

### P2：统计分析
- `GET /api/interview/practice/stats` 统计
- PracticeStats 前端面板
- 与 coverage matrix 联动（覆盖率从"有题"升级为"练过且得分≥80"）
- JD 推荐题单接入测验（从 recommendations → quiz/start）
