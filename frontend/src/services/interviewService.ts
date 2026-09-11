/** 面试线服务层（Batch 3）。

 * 职责：封装 /api/interviews、/api/interview-questions、/api/interview/simulate，
 * 并把后端 snake_case 适配为前端 camelCase 类型。
 */

import { apiClient } from "@/lib/apiClient";
import type {
  CoverageCategory,
  CoverageSkill,
  Difficulty,
  InterviewLog,
  InterviewLogCreate,
  InterviewQuestion,
  InterviewQuestionCreate,
  InterviewStats,
  QuestionCategory,
  QuestionCoverage,
  TaskDraft,
} from "@/types";

/* ───────────────────────── 后端原始结构（snake_case） ───────────────────────── */

interface InterviewLogDTO {
  id: number;
  company: string;
  role: string;
  round: string | null;
  asked_questions: string[] | null;
  weak_questions: string[] | null;
  jd_gaps: string[] | null;
  knowledge_gaps: string[] | null;
  next_actions: string[] | null;
  interviewed_at: string | null;
  notes: string | null;
  generated_task_ids: number[] | null;
  created_at: string;
  updated_at: string;
}

interface InterviewQuestionDTO {
  id: number;
  category: string;
  question: string;
  difficulty: string;
  answer_outline: string | null;
  source: string | null;
  source_day_seq: number | null;
  skill_name: string | null;
  is_verified: boolean;
  hit_count: number;
  created_at: string;
  updated_at: string;
}

interface InterviewStatsDTO {
  total_logs: number;
  total_weak: number;
  weak_topics: Array<{ topic: string; count: number; log_ids: number[] }>;
}

interface TaskDraftDTO {
  title: string;
  objective: string;
  duration: number;
  difficulty: string;
  skill_name: string | null;
  acceptance: string[];
}

interface ToTasksResultDTO {
  created: TaskDraftDTO[];
  task_ids: number[];
  count: number;
}

interface SimulateResultDTO {
  picked: InterviewQuestionDTO[];
  count: number;
}

/* ───────────────────────── 适配函数 ───────────────────────── */

function toLog(dto: InterviewLogDTO): InterviewLog {
  return {
    id: String(dto.id),
    company: dto.company,
    role: dto.role,
    round: dto.round,
    askedQuestions: dto.asked_questions || [],
    weakQuestions: dto.weak_questions || [],
    jdGaps: dto.jd_gaps || [],
    knowledgeGaps: dto.knowledge_gaps || [],
    nextActions: dto.next_actions || [],
    interviewedAt: dto.interviewed_at,
    notes: dto.notes,
    generatedTaskIds: dto.generated_task_ids || [],
    createdAt: dto.created_at,
    updatedAt: dto.updated_at,
  };
}

function toQuestion(dto: InterviewQuestionDTO): InterviewQuestion {
  return {
    id: String(dto.id),
    category: dto.category as QuestionCategory,
    question: dto.question,
    difficulty: dto.difficulty as Difficulty,
    answerOutline: dto.answer_outline,
    source: dto.source,
    sourceDaySeq: dto.source_day_seq ?? null,
    skillName: dto.skill_name ?? null,
    isVerified: dto.is_verified ?? false,
    hitCount: dto.hit_count,
    createdAt: dto.created_at,
    updatedAt: dto.updated_at,
  };
}

function toDraft(dto: TaskDraftDTO): TaskDraft {
  return {
    title: dto.title,
    objective: dto.objective,
    duration: dto.duration,
    difficulty: dto.difficulty,
    skillName: dto.skill_name,
    acceptance: dto.acceptance || [],
  };
}

/* ───────────────────────── API ───────────────────────── */

/** 面经列表。 */
export async function listLogs(): Promise<InterviewLog[]> {
  const dtos = await apiClient.get<InterviewLogDTO[]>("/api/interviews");
  return dtos.map(toLog);
}

/** 记录面经。 */
export async function createLog(payload: InterviewLogCreate): Promise<InterviewLog> {
  const dto = await apiClient.post<InterviewLogDTO>("/api/interviews", payload);
  return toLog(dto);
}

/** 删除面经。 */
export async function deleteLog(id: string): Promise<void> {
  await apiClient.delete<void>(`/api/interviews/${id}`);
}

/** 弱项统计。 */
export async function getStats(): Promise<InterviewStats> {
  const dto = await apiClient.get<InterviewStatsDTO>("/api/interviews/stats");
  return {
    totalLogs: dto.total_logs,
    totalWeak: dto.total_weak,
    weakTopics: dto.weak_topics.map((w) => ({
      topic: w.topic,
      count: w.count,
      logIds: w.log_ids || [],
    })),
  };
}

/** 弱项 → 学习任务（回写 Task）。 */
export async function toTasks(
  id: string,
  payload?: { limit?: number; duration?: number }
): Promise<{ created: TaskDraft[]; taskIds: number[]; count: number }> {
  const dto = await apiClient.post<ToTasksResultDTO>(`/api/interviews/${id}/to-tasks`, {
    limit: payload?.limit ?? 5,
    duration: payload?.duration ?? 40,
  });
  return {
    created: dto.created.map(toDraft),
    taskIds: dto.task_ids,
    count: dto.count,
  };
}

/** 题库（可按分类 / 难度过滤）。 */
export async function listQuestions(params?: {
  category?: string;
  difficulty?: string;
}): Promise<InterviewQuestion[]> {
  const qs = new URLSearchParams();
  if (params?.category) qs.set("category", params.category);
  if (params?.difficulty) qs.set("difficulty", params.difficulty);
  const query = qs.toString();
  const dtos = await apiClient.get<InterviewQuestionDTO[]>(
    `/api/interview-questions${query ? `?${query}` : ""}`
  );
  return dtos.map(toQuestion);
}

/** 新增题目。
 *
 * 注意：这里必须显式转 snake_case。apiClient 不做 key 转换，
 * 旧实现直接 post camelCase 的 `answerOutline` → 后端字段 `answer_outline` 被
 * Pydantic 当作未知字段忽略，**答题要点被静默丢弃**（P3 修复）。
 */
export async function createQuestion(
  payload: InterviewQuestionCreate
): Promise<InterviewQuestion> {
  const dto = await apiClient.post<InterviewQuestionDTO>("/api/interview-questions", {
    category: payload.category,
    question: payload.question,
    difficulty: payload.difficulty ?? "intermediate",
    answer_outline: payload.answerOutline ?? null,
    source: payload.source ?? null,
    source_day_seq: payload.sourceDaySeq ?? null,
    skill_name: payload.skillName ?? null,
    is_verified: payload.isVerified ?? false,
  });
  return toQuestion(dto);
}

/* ───────────────────────── 覆盖率（P3） ───────────────────────── */

interface QuestionCoverageDTO {
  total: number;
  target_total: number;
  core_target: number;
  core_done: number;
  per_skill_target: number;
  categories: Array<{
    key: string;
    done: number;
    target: number;
    gap: number;
    core: boolean;
  }>;
  skills: Array<{
    name: string;
    total: number;
    gap: number;
    missing: string[];
    counts: Record<string, number>;
  }>;
  cells_total: number;
  cells_filled: number;
}

/** 题库覆盖率矩阵（红格 = 缺）。默认取「主攻」赛道的技能行。 */
export async function getQuestionCoverage(
  trackKey?: string
): Promise<QuestionCoverage> {
  const qs = trackKey ? `?track_key=${encodeURIComponent(trackKey)}` : "";
  const dto = await apiClient.get<QuestionCoverageDTO>(
    `/api/interview-questions/coverage${qs}`
  );
  const categories: CoverageCategory[] = dto.categories.map((c) => ({
    key: c.key as QuestionCategory,
    done: c.done,
    target: c.target,
    gap: c.gap,
    core: c.core,
  }));
  const skills: CoverageSkill[] = dto.skills.map((s) => ({
    name: s.name,
    total: s.total,
    gap: s.gap,
    missing: s.missing ?? [],
    counts: s.counts ?? {},
  }));
  return {
    total: dto.total,
    targetTotal: dto.target_total,
    coreTarget: dto.core_target,
    coreDone: dto.core_done,
    perSkillTarget: dto.per_skill_target,
    categories,
    skills,
    cellsTotal: dto.cells_total,
    cellsFilled: dto.cells_filled,
  };
}

/** 删除题目。 */
export async function deleteQuestion(id: string): Promise<void> {
  await apiClient.delete<void>(`/api/interview-questions/${id}`);
}

/** 模拟面试抽题（命中次数 +1）。 */
export async function simulate(payload?: {
  category?: string | null;
  difficulty?: string | null;
  limit?: number;
}): Promise<{ picked: InterviewQuestion[]; count: number }> {
  const dto = await apiClient.post<SimulateResultDTO>("/api/interview/simulate", {
    category: payload?.category || null,
    difficulty: payload?.difficulty || null,
    limit: payload?.limit ?? 5,
  });
  return { picked: dto.picked.map(toQuestion), count: dto.count };
}
