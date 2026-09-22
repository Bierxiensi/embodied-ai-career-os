/** Dashboard 领域类型定义。
 *
 * 前端组件统一消费这些类型。Day6 接入 API 后，
 * services 层负责将后端 snake_case + int id 转换为前端 camelCase + string id，
 * 组件类型保持不变（数据层与展示层分离）。
 */

/** 职业目标。对应 PRD Career Management。 */
export interface Career {
  id: string;
  targetRole: string; // 目标岗位（由后端按 target_roles 的「主攻」赛道提供）
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
  /** 所属赛道（llm / vlm / ai-algo / embodied）—— 任务自身的数据。
   * null/undefined = 未归类（历史 / 手写任务）。
   * 注意：它**不是**"当前看哪个视角"的开关，不得由 ViewRole 推导出请求参数。 */
  trackKey?: string | null;
  /** 归属课程第几天（plan_days.id）。与 trackKey 正交：
   * trackKey 说「属于哪条赛道」，planDayId 说「属于课程第几天」。
   * null/undefined = 不对应任何课程日（历史 / 手写任务）。 */
  planDayId?: string | null;
}

/** 任务列表的范围口径（对应后端 GET /api/tasks 的 `scope` 参数）。
 *
 * - `all`：原始全量。冻结赛道的任务也在里面。CRUD / 审计口径，
 *   **不是**平台默认统计口径。
 * - `current_mode`：平台**默认视图口径**，由当前 CareerMode 决定
 *   （求职冲刺模式排除冻结赛道、保留未归类）。与 /jobs、/today 同源。
 *
 * 纪律：这个值只能随 **CareerMode** 变化，**绝不允许**由 ViewRole 推导 ——
 * 否则展示视角就变成了任务策略开关（Milestone B 契约）。
 */
export type TaskScopeMode = "all" | "current_mode";

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

  // ===== 决策细节（2026-09-10 新增，让"生成今日任务"可解释）=====
  /** 生成时所处的赛道 */
  trackKey: string | null;
  trackName: string | null;
  /** 赛道是否冻结（长期观察，仅低强度巩固） */
  trackFrozen: boolean;
  /** 被选中的技能：当前等级 / 要求等级 / 缺口 */
  skillLevel: number | null;
  skillTarget: number | null;
  gap: number | null;
  /** true = 复用了今天已有的同题任务（幂等命中），false = 本次新建 */
  reused: boolean;
  /** 一句话解释为什么选这个技能 */
  reason: string;
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

export interface RequiredModification {
  title: string;
  goal: string;
  files: string[];
  verification: string;
}

/** 里程碑状态（规范化后的展示口径）。
 *
 * ⚠️ 数据库里存在**两套历史词表**（2026-09-10 实测）：
 *   - 老项目（SO101）：`locked` / `in_progress` / `needs_baseline` / `completed`
 *   - 新项目（求职冲刺）：`todo` / `doing`
 * 前端在 `projectService.toMilestone` 统一归一化（todo→locked、doing→in_progress），
 * 组件只认这里的规范值，避免每处再各写一遍兼容分支。
 * 写入时一律写规范值，数据会随着编辑逐步收敛。
 */
export type MilestoneStatus =
  | "locked"
  | "in_progress"
  | "needs_baseline"
  | "completed";

export interface Milestone {
  id: string;
  projectId: string;
  version: string;
  title: string;
  goal: string;
  status: MilestoneStatus;
  sortOrder: number;
  workspace?: string | null;
  requiredModifications?: RequiredModification[];
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

// ===== 求职看板（Job Hunt Dashboard）=====

/** 求职投递状态机：applied → screening → interview → offer，任意阶段可 rejected。 */
export type JobAppStatus =
  | "applied"
  | "screening"
  | "interview"
  | "offer"
  | "rejected";

/** 目标岗位画像（来自后端 TARGET_ROLES 配置 + 实时匹配度计算）。 */
export interface TargetRole {
  key: string;
  name: string;
  priority: "主攻" | "卡位" | "保底" | "暂缓";
  salaryRange: string;
  note: string;
  matchPct: number;
  strictPct: number;        // v3.2 双轨口径：硬性达标率（level>=required 的技能占比）
  qualifiedCount: number;   // 达标技能数
  requiredCount: number;    // 要求技能总数
  frozen?: boolean;   // 冻结赛道：保留展示与匹配度，但不投入学习时间
  skills: Array<{
    name: string;
    level: number;
    required: number;
    gap: number;
    missing: boolean;
  }>;
}

/** 技能缺口项（按 gap 降序）。 */
export interface SkillGap {
  name: string;
  category: string;
  level: number;
  targetLevel: number;
  gap: number;
  evidence: string[];
}

/** 求职项目里程碑。 */
export interface JobMilestone {
  id: string;
  version: string;
  title: string;
  goal: string;
  status: string;
  sortOrder: number;
}

/** 求职项目（含里程碑进度）。 */
export interface JobProject {
  id: string | null;
  name: string | null;
  currentVersion: string | null;
  milestones: JobMilestone[];
  milestoneTotal: number;
  milestoneCompleted: number;
}

/** 求职任务摘要项。 */
export interface JobTaskItem {
  id: string;
  title: string;
  skillName: string | null;
  status: string;
  duration: number | null;
  objective: string | null;
  /** 所属赛道（llm / vlm / ai-algo / embodied）；null = 未归类 */
  trackKey?: string | null;
  /** 后端给出的归类（active / frozen / unclassified）。
   * 前端**只展示**，绝不自己拿 trackKey 重算 —— 规则只有后端一份。 */
  scope?: TaskTrackScope;
}

/* ─────────────────── 任务赛道口径（Task Scope · Milestone B）─────────────────── */

/** 一条任务相对当前阶段的归类。
 *
 * - `active`：已归类且未被冻结 → 进入默认视图
 * - `frozen`：冻结赛道 → 不进默认视图，但被计数、可查看
 * - `unclassified`：无赛道的历史 / 手写任务 → 进入默认视图并标记
 */
export type TaskTrackScope = "active" | "frozen" | "unclassified";

/** 本次响应用的赛道口径 + 透明度计数（后端 services/action_planning/task_scope.py）。 */
export interface TaskScopeSummary {
  modeKey: string;
  modeName: string;
  /** 是否实际限缩了任务范围（= 本阶段存在冻结赛道） */
  isTrackScoped: boolean;
  activeTrackKeys: string[];
  frozenTrackKeys: string[];
  /** 口径说明（人话），直接展示即可 */
  scopeReason: string;
  /** 纳入口径的任务数 */
  included: number;
  /** 被排除的冻结赛道任务数 */
  frozenExcluded: number;
  /** 其中「未归类」的任务数 */
  unclassified: number;
}

/** 被口径排除的任务的最小识别信息（PRD F5.3：隐藏不等于删除，可查看）。 */
export interface ScopedTaskRef {
  id: string;
  title: string;
  trackKey: string | null;
  status: string;
  scope: TaskTrackScope;
}

/** 一条投递记录。 */
export interface JobApplication {
  id: string;
  company: string;
  role: string;
  track: string;
  source: string | null;
  status: JobAppStatus;
  salaryRange: string | null;
  appliedAt: string | null;
  nextAction: string | null;
  notes: string | null;
  createdAt: string;
  updatedAt: string;
}

/** 求职看板聚合数据（GET /api/job-hunt）。 */
/** 雷达图的一个轴：来自「主攻赛道」的硬性技能要求。
 *
 * 雷达轴不再取全量技能（48 项 → 46 轴不可读），而是取目标岗位的 required_skills，
 * 直接回答"离目标岗位的技能形状差多少"。
 */
export interface RadarAxis {
  name: string;
  current: number;
  required: number;
  gap: number;
}

/** 当前视角对应的赛道摘要（驱动雷达轴与匹配度口径，保证与 /jobs 页同源）。
 *
 * 命名从 `PrimaryTrack` 改为 `ActiveTrack`：视角可切换到具身赛道，
 * 此时它并不是「主攻」赛道，旧名字会产生误导。
 */
export interface ActiveTrack {
  key: string;
  name: string;
  priority: string;
  matchPct: number;
  /** v3.2 双轨口径：硬性达标率（level>=required 的技能占比），与 JobsBoard 同源 */
  strictPct?: number;
  /** 达标技能数（v3.2） */
  qualifiedCount?: number;
  /** 冻结赛道（长期观察）：只看不推，不占用主攻缺口 */
  frozen?: boolean;
  /** 该赛道硬性要求技能数（= 雷达轴数） */
  skillCount: number;
  /** 其中仍存在缺口（gap>0）的技能数 */
  gapCount: number;
}

/** 视角角色 —— 同一份能力数据的两种**观察方式**（纯展示层）。
 *
 * - `jobhunt`：求职冲刺（默认）。对齐「主攻」赛道，服务于当前 offer 目标。
 * - `embodied`：具身智能。对齐冻结的长期赛道，用于随时盘点与巩固基础。
 *
 * 纪律（Milestone B 收尾，2026-09-16 收紧）：
 * **ViewRole 是展示视角，不是策略开关。** 它只允许影响"看什么"——
 * 标题文案、雷达轴、就绪度标签、项目视觉强调。
 * 它**不得**影响：任务请求参数、任务数据范围、任务统计、推荐。
 * 任务的业务策略（生效/冻结赛道）唯一来源是 CareerMode
 * （见 `services/action_planning/task_scope.py`），前端不得用 ViewRole 推导过滤。
 */
export type ViewRole = "jobhunt" | "embodied";


/** 视角切换器的选项（由后端返回的赛道配置派生，前端不硬编码赛道 key）。 */
export interface ViewRoleOption {
  role: ViewRole;
  label: string;
  /** 一句话说明这个视角是干什么用的，显示在切换器下方 */
  description: string;
  /** 后端是否提供了对应赛道（false 时该视角不可点） */
  available: boolean;
  trackKey: string | null;
  trackName: string | null;
  matchPct: number | null;
  /** 长期视角（冻结赛道）：UI 上标注「长期」，避免与冲刺目标混淆 */
  isLongTerm: boolean;
}

/** 求职看板聚合数据（GET /api/job-hunt）。 */
export interface JobHuntBoard {
  career: {
    targetRole: string | null;
    salaryTarget: number | null;
    timeframe: string | null;
    notes: string | null;
  } | null;
  offerDeadline: string;
  daysLeft: number;
  targetRoles: TargetRole[];
  skillGaps: SkillGap[];
  jobProject: JobProject | null;
  tasks: {
    total: number;
    done: number;
    doing: number;
    todo: number;
    /** 被口径排除的冻结赛道任务数（具身），见 backend/app/api/job_hunt.py。 */
    frozenExcluded: number;
    /** 未归类（无赛道）任务数：始终计入默认视图，此处仅提示 */
    unclassified: number;
    items: JobTaskItem[];
    /** 被排除任务本身（可查看，不是删除） */
    frozenItems: ScopedTaskRef[];
    /** 口径自描述：解释"总数为什么变化"，前端不重算 */
    scope: TaskScopeSummary;
  };
  applications: {
    total: number;
    byStatus: Record<JobAppStatus, number>;
    responseRate: number;
    items: JobApplication[];
  };
  jobPool?: JobPoolSummary;
}

/** 新建投递记录入参。 */
export interface JobApplicationCreate {
  company: string;
  role: string;
  track?: string;
  source?: string | null;
  status?: JobAppStatus;
  salaryRange?: string | null;
  appliedAt?: string | null;
  nextAction?: string | null;
  notes?: string | null;
}

// ===== 岗位池（Job Posting Pool · Batch 1）=====

/** 战略梯队（与 target_roles 对齐）。 */
export type PostingTier = 1 | 2 | 3;

/** 匹配等级。 */
export type MatchGrade = "A" | "B" | "C" | "D";

/** 5 维分项键。 */
export interface DimensionScores {
  tech_stack: number;
  project: number;
  edu_exp: number;
  research: number;
  industry: number;
}

/** 单条差距。 */
export interface MatchGap {
  skill: string;
  level: number;
  required: number;
  gap: number;
}

/** 一条岗位（内联匹配）。GET /api/job-postings 响应项。 */
export interface JobPosting {
  id: string;
  company: string;
  title: string;
  city: string | null;
  salaryRange: string | null;
  jdText: string | null;
  source: string | null;
  url: string | null;
  postedAt: string | null;
  tier: PostingTier;
  track: string;
  requiredSkills: string[] | null;
  education: string | null;
  minYears: number | null;
  paperRequired: boolean;
  status: string;
  createdAt: string;
  updatedAt: string;
  // 内联匹配
  matchScore: number | null;
  grade: MatchGrade | null;
  dimensionScores: DimensionScores | null;
  gaps: MatchGap[] | null;
  matchedTrack: string | null;
  matchedAt: string | null;
}

/** 岗位池统计（GET /api/job-postings/stats）。 */
export interface JobPoolStats {
  total: number;
  byTier: Record<PostingTier, number>;
  byGrade: Record<MatchGrade, number>;
  recommended: number;
  unmatched: number;
}

/** 岗位池聚合（/api/job-hunt 内嵌的 job_pool 摘要）。 */
export interface JobPoolSummary {
  total: number;
  byGrade: Record<MatchGrade, number>;
  recommended: number;
  top: Array<{
    id: string;
    company: string;
    title: string;
    track: string;
    tier: PostingTier;
    matchScore: number;
    grade: MatchGrade;
  }>;
}

/** 新建岗位入参（POST /api/job-postings）。 */
export interface JobPostingCreateInput {
  company: string;
  title: string;
  jdText?: string | null;
  track?: string;
  tier?: PostingTier;
  city?: string | null;
  salaryRange?: string | null;
  source?: string | null;
  url?: string | null;
  education?: string | null;
  minYears?: number | null;
  paperRequired?: boolean;
  requiredSkills?: string[] | null;
  status?: string;
}

// ===== 简历线（Resume · Batch 2）=====

/** 事实分类。 */
export type FactCategory = "work" | "project" | "paper" | "edu" | "metric";

/** 一条事实锚点（防虚构依据）。 */
export interface ResumeFact {
  id: string;
  category: FactCategory;
  title: string;
  org: string | null;
  start: string | null;
  end: string | null;
  facts: string[];
  source: string | null;
  createdAt: string;
  updatedAt: string;
}

/** 一份简历版本。 */
export interface ResumeVersion {
  id: string;
  name: string;
  contentMd: string | null;
  targetTier: PostingTier;
  isPrimary: boolean;
  createdAt: string;
  updatedAt: string;
}

/** 一条诊断出的 claim 及其锚定结果。 */
export interface ResumeClaim {
  text: string;
  anchored: boolean;
  anchors: Array<{ factId: number; title: string; category: string }>;
  reason: string;
}

/** JD 要求技能的简历依据情况。 */
export interface JdAlignmentItem {
  skill: string;
  supported: boolean;
  evidence: string | null;
}

/** 防虚构诊断结果。 */
export interface ResumeDiagnosis {
  total: number;
  anchoredCount: number;
  unanchoredCount: number;
  fabricationRisk: number; // 0-100（未锚定占比）
  claims: ResumeClaim[];
  jdAlignment: JdAlignmentItem[] | null;
}

/** 新建简历版本入参（POST /api/resume/versions）。 */
export interface ResumeVersionCreate {
  name: string;
  contentMd?: string | null;
  targetTier?: PostingTier;
  isPrimary?: boolean;
}

/** 新增事实锚点入参（POST /api/resume/facts）。 */
export interface ResumeFactCreate {
  category: FactCategory;
  title: string;
  org?: string | null;
  start?: string | null;
  end?: string | null;
  facts: string[];
  source?: string | null;
}

/** 诊断入参（POST /api/resume/diagnose）。 */
export interface ResumeDiagnoseIn {
  versionId?: string | null;
  contentMd?: string | null;
  postingId?: string | null;
}

// ===== 面试线（Interview · Batch 3）=====

/** 题库分类。 */
export type QuestionCategory = "LLM" | "Multimodal" | "Project" | "Coding";

/** 难度。 */
export type Difficulty = "beginner" | "intermediate" | "advanced";

/** 题型。 */
export type QuestionType = "open" | "choice" | "fill" | "judge";

/** 一道面试题（题库）。 */
export interface InterviewQuestion {
  id: string;
  category: QuestionCategory;
  question: string;
  difficulty: Difficulty;
  answerOutline: string | null;
  source: string | null;
  /** P2：归属课程日序号（1..30），用于「四件套 questions 自动判定」 */
  sourceDaySeq: number | null;
  /** P2：关联技能名（题库覆盖率矩阵的行 + evidence-gated） */
  skillName: string | null;
  /** P2：是否通过面试验收验证 */
  isVerified: boolean;
  hitCount: number;
  /** 题型：open / choice / fill / judge */
  questionType: QuestionType;
  /** 手动配置的选项（仅 choice 类型） */
  options: { choices: string[]; correct: string } | null;
  createdAt: string;
  updatedAt: string;
}

/** 一次面试记录（面经）。 */
export interface InterviewLog {
  id: string;
  company: string;
  role: string;
  round: string | null;
  askedQuestions: string[];
  weakQuestions: string[];
  jdGaps: string[];
  knowledgeGaps: string[];
  nextActions: string[];
  interviewedAt: string | null;
  notes: string | null;
  generatedTaskIds: number[];
  createdAt: string;
  updatedAt: string;
}

/** 一条聚合弱项。 */
export interface WeakTopic {
  topic: string;
  count: number;
  logIds: number[];
}

/** 弱项统计（GET /api/interviews/stats）。 */
export interface InterviewStats {
  totalLogs: number;
  totalWeak: number;
  weakTopics: WeakTopic[];
}

/** 学习任务草稿（弱项回写）。 */
export interface TaskDraft {
  title: string;
  objective: string;
  duration: number;
  difficulty: string;
  skillName: string | null;
  acceptance: string[];
}

/** 新建面经入参。 */
export interface InterviewLogCreate {
  company: string;
  role: string;
  round?: string | null;
  askedQuestions?: string[];
  weakQuestions?: string[];
  jdGaps?: string[];
  knowledgeGaps?: string[];
  nextActions?: string[];
  interviewedAt?: string | null;
  notes?: string | null;
}

/** 新增题目入参。 */
export interface InterviewQuestionCreate {
  category: QuestionCategory;
  question: string;
  difficulty?: Difficulty;
  answerOutline?: string | null;
  source?: string | null;
  /** P2/P3：可选归属课程日与关联技能（快速录题时顺手带） */
  sourceDaySeq?: number | null;
  skillName?: string | null;
  isVerified?: boolean;
}

// ===== 题库覆盖率（Question · P3）=====

/** 一个分类的进度（done vs target）。 */
export interface CoverageCategory {
  key: QuestionCategory;
  done: number;
  target: number;
  gap: number;
  core: boolean;
}

/** 覆盖率矩阵中的一行（技能 × 四分类）。 */
export interface CoverageSkill {
  name: string;
  total: number;
  gap: number;
  /** 红格：该技能在这些分类里一题为 0 */
  missing: string[];
  counts: Record<string, number>;
}

/** 题库覆盖率总览（GET /api/interview-questions/coverage）。 */
export interface QuestionCoverage {
  total: number;
  targetTotal: number;
  coreTarget: number;
  coreDone: number;
  perSkillTarget: number;
  categories: CoverageCategory[];
  skills: CoverageSkill[];
  cellsTotal: number;
  cellsFilled: number;
}

// ===== 练习与测验（Practice）=====

/** 单题答题结果。 */
export interface PracticeResult {
  correct: boolean;
  score: number;
  maxScore: number;
  feedback: string;
  correctAnswer: string;
  outlineCovered: string[];
  outlineMissed: string[];
  recordId: number;
}

/** 测验中的单题（不含参考答案）。 */
export interface QuizQuestion {
  id: number;
  question: string;
  questionType: QuestionType;
  options: string[] | null;
  skillName: string | null;
  difficulty: string;
}

/** 测验开始响应。 */
export interface QuizStart {
  sessionId: string;
  questions: QuizQuestion[];
  count: number;
}

/** 测验中的一条答题记录。 */
export interface QuizRecord {
  questionId: number;
  questionType: QuestionType;
  question: string;
  userAnswer: string;
  correctAnswer: string | null;
  correct: boolean;
  score: number;
  feedback: string | null;
}

/** 某题型的测验统计。 */
export interface QuizTypeStats {
  count: number;
  correct: number;
  avgScore: number;
}

/** 测验结果。 */
export interface QuizResult {
  sessionId: string;
  totalScore: number;
  count: number;
  correctCount: number;
  byType: Record<string, QuizTypeStats>;
  weakSkills: string[];
  records: QuizRecord[];
}

/** 某题型的练习统计。 */
export interface PracticeTypeStats {
  practiced: number;
  correct: number;
  accuracy: number;
}

/** 某技能的练习统计。 */
export interface PracticeSkillStats {
  skill: string;
  practiced: number;
  correct: number;
  accuracy: number;
}

/** 测验摘要。 */
export interface PracticeSessionSummary {
  sessionId: string;
  date: string;
  score: number;
  count: number;
}

/** 练习总统计。 */
export interface PracticeStats {
  totalPracticed: number;
  totalCorrect: number;
  accuracy: number;
  byType: Record<string, PracticeTypeStats>;
  bySkill: PracticeSkillStats[];
  weakSkills: string[];
  weakTypes: string[];
  recentSessions: PracticeSessionSummary[];
}

// ===== 日报 / 周报（Report · Batch 4）=====

/** 报告类型。 */
export type ReportKind = "daily" | "weekly";

/** 报告中的一段。 */
export interface ReportSection {
  key: string;
  title: string;
  lines: string[];
}

/** 即时构建的报告（GET /api/reports/daily | /weekly）。 */
export interface Report {
  kind: ReportKind;
  periodKey: string;
  title: string;
  sections: ReportSection[];
  metrics: Record<string, unknown>;
  generatedAt: string;
}

/** 归档报告（GET /api/reports/history）。 */
export interface ReportLog {
  id: string;
  kind: ReportKind;
  periodKey: string;
  title: string;
  body: string;
  sections: ReportSection[] | null;
  metrics: Record<string, unknown> | null;
  sent: boolean;
  sentAt: string | null;
  generatedAt: string | null;
}

/** 待跟进投递。 */
export interface Followup {
  id: string;
  company: string;
  role: string;
  status: string;
  nextAction: string | null;
  reason: string;
  days: number;
  overdue: boolean;
}

/** 待跟进汇总（GET /api/reports/followups）。 */
export interface FollowupResult {
  staleDays: number;
  count: number;
  items: Followup[];
}

/** 调度器中的一个 job。 */
export interface SchedulerJob {
  id: string;
  trigger: string;
  nextRun: string | null;
}

/** 报告调度总览（GET /api/reports/schedule）。 */
export interface ReportSchedule {
  enabled: boolean;
  dailyTime: string;
  weeklyDay: string;
  weeklyTime: string;
  followupTime: string;
  followupStaleDays: number;
  channel: string;
  jobs: SchedulerJob[];
}

/** 推送结果（POST /api/reports/{kind}/send）。 */
export interface SendResult {
  kind: ReportKind;
  periodKey: string;
  sent: boolean;
  skipped: boolean;
  reason: string | null;
  title: string | null;
}

/* ══════════════════════════════════════════════════════════════
   30 天施工执行台（见 docs/platform-direction-30day.md）
   对应 backend /api/plan 系列端点。
   ══════════════════════════════════════════════════════════════ */

/** 课程日（Day 1..30）。seq 是不可变的课程序号，与日历日期无关。 */
export interface PlanDay {
  id: string;
  seq: number;
  phase: number; // 阶段（周）1..4
  phaseName: string; // 阶段名，如「第一周 · 打穿 Transformer」
  title: string; // 当天主题
  theme: string; // 技术域
  objectives: string[]; // 学习目标
  acceptance: string[]; // 验收标准
  interviewTopics: string[]; // 当天必须能回答的面试题主题
  resources: string[]; // 指定资源（严格来自 5 类资源锁）
  estMinutes: number; // 预计投入分钟数
  trackKey: string; // 归属赛道 llm / vlm
}

/** 每日四件套的产出类型（计划 §十）。 */
export type ArtifactKind = "code" | "note" | "questions" | "commit";

/** 四件套的展示口径（顺序与后端 ARTIFACT_KINDS 一致）。 */
export const ARTIFACT_META: {
  kind: ArtifactKind;
  label: string;
  hint: string;
}[] = [
  { kind: "code", label: "代码", hint: "一段可运行的代码" },
  { kind: "note", label: "笔记", hint: "一页技术笔记" },
  { kind: "questions", label: "面试题", hint: "至少 5 道" },
  { kind: "commit", label: "commit", hint: "一次 git 提交" },
];

/** 一条每日产出。 */
export interface DayArtifact {
  id: string;
  planDayId: string;
  kind: ArtifactKind;
  title?: string;
  url?: string;
  autoVerified: boolean; // P0 恒 false；P2 起 commit / questions 可自动核验
  note?: string;
  createdAt: string;
}

/** 「总账」一行：某项产出的累计进度（30 天口径）。 */
export interface LedgerItem {
  key: string; // code / note / commit / questions / days
  label: string;
  done: number;
  target: number;
}

/** 今日施工单视图（GET /api/plan/today）。
 * 回答三个问题：今天第几天、今天干什么、今天做完没有。 */
export interface TodayView {
  day: PlanDay;

  /** 今天算课程第几天（P0 由日历推导，clamp 到 1..30） */
  dayIndex: number;
  totalDays: number;

  /** 日历口径，用于偏差提示（P1 起支持落后量决策） */
  calendarDaysElapsed: number;
  sprintStart: string;
  isBeforeStart: boolean;
  isAfterEnd: boolean;

  /** 今日任务（tasks.plan_day_id == 当天，且经当前阶段的赛道口径） */
  tasks: Task[];
  completedTasks: number;

  /** 任务赛道口径（Milestone B）：与 /api/job-hunt 同源。
   * 可选 —— 老响应没有该字段时页面照常渲染（向后兼容）。 */
  taskScope?: TaskScopeSummary | null;
  /** 被口径排除、因而**不在** tasks 里的任务（可查看） */
  excludedTasks?: ScopedTaskRef[];

  /** 四件套状态 */
  artifacts: DayArtifact[];
  artifactStatus: Record<string, number>;
  /** P2：题库中归属当天的题目条数（questions 轴自动判定用） */
  questionsFromBank: number;
  missingKinds: ArtifactKind[];
  allDone: boolean;

  /** 总账（跨全部 30 天累计） */
  ledger: LedgerItem[];
}

/** 一天课程的进度状态（GET /api/plan/overview 的 days[] 元素）。 */
export type DayProgressStatus =
  | "pending"
  | "done"
  | "compressed"
  | "deferred"
  | "skipped";

/** 一天课程的进度投影（P1 滑期总览用）。 */
export interface PlanDayStatus {
  seq: number;
  planDayId: string;
  phase: number;
  phaseName: string;
  title: string;
  theme: string;
  trackKey: string;
  estMinutes: number;
  status: DayProgressStatus;
  fullArtifacts: boolean; // 四件套是否齐全（推导 done 的依据之一）
  isMissed: boolean; // seq <= 当前天 且未通过 → 已错过，需要决策
  deviationNote?: string | null;
}

/** 30 天总览（课程进度 vs 日历进度）。 */
export interface PlanOverview {
  dayIndex: number; // 日历推导的「今天算课程第几天」
  totalDays: number;
  sprintStart: string;
  sprintEnd: string;
  calendarDaysElapsed: number;
  isBeforeStart: boolean;
  isAfterEnd: boolean;
  behind: number; // 已错过的天数（>0 即落后）
  completedDays: number; // 已通过（done/compressed）且 seq <= dayIndex 的天数
  days: PlanDayStatus[];
}

/* ══════════════════════════════════════════════════════════════
   证据闭环 P2（experiments / evidence-gated / commit 同步）
   ══════════════════════════════════════════════════════════════ */

/** 实验类型（决策 4：实验是一等公民）。 */
export type ExperimentKind = "finetune" | "benchmark" | "ablation";

/** 实验变体（对比表的一行）。字段开放，渲染器按 key 出列。 */
export interface ExperimentVariant {
  name: string;
  [key: string]: unknown;
}

/** 实验指标（{name, value, unit}）。 */
export interface ExperimentMetric {
  name: string;
  value: unknown;
  unit?: string;
}

/** 一条实验记录（对应后端 experiments 表）。 */
export interface Experiment {
  id: string;
  planDayId: string | null;
  daySeq: number;
  name: string;
  kind: ExperimentKind;
  skillName: string | null;
  variants: ExperimentVariant[];
  metrics: ExperimentMetric[];
  conclusion: string | null;
  artifactIds: string[];
  createdAt: string;
  updatedAt: string;
}

/** 新增实验入参。 */
export interface ExperimentCreate {
  planDayId?: string | null;
  daySeq: number;
  name: string;
  kind: ExperimentKind;
  skillName?: string | null;
  variants?: ExperimentVariant[];
  metrics?: ExperimentMetric[];
  conclusion?: string | null;
  artifactIds?: string[];
}

/** commit 同步结果。 */
export interface CommitSyncResult {
  synced: number;
  skipped?: boolean;
  reason?: string;
  error?: string;
  source?: string;
  repo?: string;
}

/** 一条 typed evidence（「技能升级因为这份代码」的文案来源）。 */
export interface SkillEvidenceItem {
  level: number; // 1..4
  kind: string; // note / question / code / experiment / research
  label: string; // 能解释 / 能实现修改 / 能做实验 / 能研究
  ref: string; // 具体证据描述
}

/** 单个技能的 evidence-gated 推导。 */
export interface SkillEvidence {
  id: string;
  name: string;
  level: number;
  targetLevel: number;
  evidenceGate: number; // 0..4，从真实证据推导的最高可信等级
  evidence: SkillEvidenceItem[];
}

/* ───────────────────── P4 求职包装（README / 简历技能行） ───────────────────── */

/** README 骨架生成的输入统计（让用户看清"哪些部分已自动填好"）。 */
export interface ReadmeCounts {
  milestones: number;
  skills: number;
  skillsWithEvidence: number;
  experiments: number;
  chars: number;
}

/** 项目 README：savedReadme = 已保存的，draft = 本次从证据链重新生成的。 */
export interface ProjectReadme {
  projectId: string;
  name: string;
  savedReadme: string | null;
  draft: string;
  counts: ReadmeCounts;
}

/** 一条可写进简历的技能行（已附证据）。 */
export interface SkillLine {
  skill: string;
  level: number;
  category: string | null;
  gateLevel: number;
  line: string;
  refs: SkillEvidenceItem[];
}

/** 自评较强但尚无证据的技能 —— 写进简历即构成虚构风险。 */
export interface SkillLinePending {
  skill: string;
  level: number;
  category: string | null;
  gateLevel: number;
  missing: string;
}

/** 简历技能行总览。 */
export interface SkillLineReport {
  ready: SkillLine[];
  pending: SkillLinePending[];
  summary: {
    total: number;
    ready: number;
    pending: number;
    pendingMinLevel: number;
  };
  note: string;
}

/* ───────────────────────── 职业阶段模式（Career Mode） ───────────────────────── */

/** 阶段模式 key。
 *
 * 唯一来源是后端 app/services/career_mode/presets.py；这里保留 string 兜底，
 * 后端新增模式时前端不会因联合类型不匹配而编译失败。
 */
export type CareerModeKey = "job_hunt" | "long_term_transition";

/** 一个职业阶段 —— 当前阶段的北极星目标与期限。
 *
 * 与 ViewRole 的区别（两者不是同一件事，不要混用）：
 * - `ViewRole`（lib/viewRole.ts）：Dashboard 的**观察视角**，存 cookie，
 *   只影响"看哪张图"，不落库。
 * - `CareerMode`：产品**阶段**，存后端数据库，影响全局导航与默认推荐口径。
 *   切换它不会删除、修改或隐藏任何既有业务数据。
 */
export interface CareerMode {
  id: string;
  key: CareerModeKey | string;
  name: string;
  objective: string;
  /** ISO 日期；null = 该阶段无硬截止（长期模式按季度 / 里程碑推进） */
  deadline: string | null;
  /** 距 deadline 的天数，由后端推导；无 deadline 时为 null。
   *  刻意不在前端重算 —— 否则两边取整不一致会被当成 bug 反复排查。 */
  daysLeft: number | null;
  /** 该阶段推动的赛道 key；Milestone A 只展示、不执行过滤 */
  activeTrackKeys: string[];
  /** 该阶段冻结的赛道 key：只看不推，历史资产保留 */
  frozenTrackKeys: string[];
  isCurrent: boolean;
}

/** GET /api/career-mode 的返回：当前模式 + 可切换的全部模式。 */
export interface CareerModeOverview {
  current: CareerMode;
  available: CareerMode[];
}

/** 一次模式切换的历史记录。fromMode 为 null 表示系统首次激活默认模式。 */
export interface CareerModeTransition {
  id: string;
  fromMode: string | null;
  toMode: string;
  transitionedAt: string;
  note: string | null;
}

/** 切换成功的返回：切换后的模式 + 本次切换记录。 */
export interface CareerModeSwitchResult {
  current: CareerMode;
  transition: CareerModeTransition;
}
