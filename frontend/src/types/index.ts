/** Dashboard 领域类型定义。
 *
 * 前端组件统一消费这些类型。Day6 接入 API 后，
 * services 层负责将后端 snake_case + int id 转换为前端 camelCase + string id，
 * 组件类型保持不变（数据层与展示层分离）。
 */

/** 职业目标。对应 PRD Career Management。 */
export interface Career {
  id: string;
  targetRole: string; // 目标岗位，如 Robot AI Engineer
  salaryTarget: number; // 薪资目标（RMB/月）
  timeframe: string; // 时间规划，如 "2027" / "6 months"
  progress: number; // 整体达成度 0-100（Day6 暂用固定值，Day7 由 Reviewer 计算）
}

/** 技能节点。对应 PRD Skill Graph。
 * level / targetLevel 用 0-5 整数对应 MY_CONTEXT 星级（★★★★★ = 5）。
 * evidence 记录能力证明（项目/GitHub/作品），用于生成能力证明图谱。
 */
export interface Skill {
  id: string;
  name: string; // 技能名称，如 ROS2
  category: string; // 分类：Strong / Medium / Weak
  level: number; // 当前等级 0-5
  targetLevel: number; // 目标等级 0-5
  evidence: string[]; // 能力证明项
}

/** 任务状态机：todo → doing → done。 */
export type TaskStatus = "todo" | "doing" | "done";

/** 学习任务。对应 PRD AI Planner 每日生成的核心任务。
 * acceptance 为验收标准清单，避免沦为学习记录工具。
 */
export interface Task {
  id: string;
  title: string; // 任务标题
  skill: string; // 关联技能名称
  duration: number; // 预计时长（分钟）
  acceptance: string[]; // 验收标准清单
  status: TaskStatus;
  objective?: string; // 学习目标
  difficulty?: string; // 难度
  resources?: string[]; // 推荐资源
  projectId?: string | null; // V2: 关联项目
  milestoneId?: string | null; // V2: 关联里程碑
}

/** Planner Agent 输入技能项（snake_case，匹配后端契约）。 */
export interface PlannerSkillInput {
  name: string;
  level: number;
  target: number;
}

/** Planner Agent 生成结果。 */
export interface PlannerResult {
  title: string;
  skill: string;
  objective: string | null;
  duration: number;
  difficulty: string | null;
  acceptance: string[];
  resources: string[];
  status: string;
  taskId: number | null; // 持久化后的任务 ID
}

/** 学习日志。Day7 Reviewer Agent 的输入，AI Engineer Portfolio 证据。 */
export interface LearningLog {
  id: string;
  taskId: string | null;
  content: string;
  durationMinutes: number | null;
  artifactUrl: string | null;
  createdAt: string;
}

/** 技能评估记录。Day7 Reviewer 产出的中间层，记录等级变更依据。 */
export interface SkillAssessment {
  id: string;
  skillId: string;
  taskId: string | null;
  oldLevel: number;
  newLevel: number;
  confidence: number;
  reason: string;
  evidenceScore: number;
  createdAt: string;
}

/** Reviewer 评估结果（POST /api/reviewer/review 响应）。 */
export interface ReviewerResult {
  task: {
    id: number;
    title: string;
    skillName: string | null;
    status: string;
  };
  learningLog: LearningLog;
  assessment: SkillAssessment;
  updatedSkill: {
    id: number;
    name: string;
    level: number;
    targetLevel: number;
    evidence: string[];
  };
}

// ===== Phase 2 Day6：Agent Observability =====

/** Agent 执行记录（GET /api/agent/runs 响应项）。 */
export interface AgentRunRecord {
  id: string;
  agentName: string;           // planner / reviewer / career / research / supervisor
  status: string;              // success / failed
  durationMs: number;          // 耗时（毫秒）
  traceId: string | null;      // 追踪 ID（旧数据为 null）
  createdAt: string;           // ISO 时间字符串
  outputSummary: string;       // 输出摘要（前 80 字符）
  inputContext: Record<string, unknown>;
  outputResult: Record<string, unknown>;
}

/** Agent Activity 查询结果。 */
export interface AgentActivity {
  total: number;
  runs: AgentRunRecord[];
}

// ===== V2: Project Management =====

export interface Milestone {
  id: string;
  projectId: string;
  version: string;
  title: string;
  goal: string;
  status: "locked" | "in_progress" | "completed";
  sortOrder: number;
}

export interface Project {
  id: string;
  name: string;
  goal: string;
  description: string | null;
  status: "active" | "paused" | "completed";
  currentVersion: string;
  githubUrl: string | null;
  readme: string | null;
  sortOrder: number;
  milestones: Milestone[];
  milestoneTotal: number;
  milestoneCompleted: number;
  progressPct: number;
}

// ===== V2: GitHub Commit 感知 =====

/** GitHub commit 关联建议。 */
export interface CommitSuggestion {
  id: string;
  commitSha: string;
  commitMessage: string;
  repo: string;
  aiSuggestions: Array<{
    skill: string;
    reason: string;
    confidence: number;
  }>;
  summary: string | null;
  createdAt: string | null;
}
