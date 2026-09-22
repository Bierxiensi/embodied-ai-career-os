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
  PracticeResult,
  PracticeStats,
  QuestionCategory,
  QuestionCoverage,
  QuestionType,
  QuizResult,
  QuizStart,
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
  question_type: string;
  options: { choices: string[]; correct: string } | null;
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
    questionType: (dto.question_type || "open") as QuestionType,
    options: dto.options ?? null,
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

/** 题库（可按分类 / 难度 / 来源过滤）。 */
export async function listQuestions(params?: {
  category?: string;
  difficulty?: string;
  source?: string;
}): Promise<InterviewQuestion[]> {
  const qs = new URLSearchParams();
  if (params?.category) qs.set("category", params.category);
  if (params?.difficulty) qs.set("difficulty", params.difficulty);
  if (params?.source) qs.set("source", params.source);
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

/** 更新题目（标记已练习 / 已验证 / 改分类等）。 */
export async function updateQuestion(
  id: string,
  patch: {
    category?: string;
    difficulty?: string;
    answerOutline?: string | null;
    source?: string | null;
    sourceDaySeq?: number | null;
    skillName?: string | null;
    isVerified?: boolean;
    hitCount?: number;
  }
): Promise<InterviewQuestion> {
  const dto = await apiClient.patch<InterviewQuestionDTO>(
    `/api/interview-questions/${id}`,
    {
      ...(patch.category !== undefined && { category: patch.category }),
      ...(patch.difficulty !== undefined && { difficulty: patch.difficulty }),
      ...(patch.answerOutline !== undefined && { answer_outline: patch.answerOutline }),
      ...(patch.source !== undefined && { source: patch.source }),
      ...(patch.sourceDaySeq !== undefined && { source_day_seq: patch.sourceDaySeq }),
      ...(patch.skillName !== undefined && { skill_name: patch.skillName }),
      ...(patch.isVerified !== undefined && { is_verified: patch.isVerified }),
      ...(patch.hitCount !== undefined && { hit_count: patch.hitCount }),
    }
  );
  return toQuestion(dto);
}

/** 模拟面试抽题（命中次数 +1）。 */
export async function simulate(payload?: {
  category?: string | null;
  difficulty?: string | null;
  skillName?: string | null;
  limit?: number;
}): Promise<{ picked: InterviewQuestion[]; count: number }> {
  const dto = await apiClient.post<SimulateResultDTO>("/api/interview/simulate", {
    category: payload?.category || null,
    difficulty: payload?.difficulty || null,
    skill_name: payload?.skillName || null,
    limit: payload?.limit ?? 5,
  });
  return { picked: dto.picked.map(toQuestion), count: dto.count };
}

/* ───────────────────────── 练习与测验 ───────────────────────── */

interface PracticeResultDTO {
  correct: boolean;
  score: number;
  max_score: number;
  feedback: string;
  correct_answer: string;
  outline_covered: string[];
  outline_missed: string[];
  record_id: number;
}

interface QuizQuestionDTO {
  id: number;
  question: string;
  question_type: string;
  options: string[] | null;
  skill_name: string | null;
  difficulty: string;
}

interface QuizStartDTO {
  session_id: string;
  questions: QuizQuestionDTO[];
  count: number;
}

interface QuizRecordDTO {
  question_id: number;
  question_type: string;
  question: string;
  user_answer: string;
  correct_answer: string | null;
  correct: boolean;
  score: number;
  feedback: string | null;
}

interface QuizResultDTO {
  session_id: string;
  total_score: number;
  count: number;
  correct_count: number;
  by_type: Record<string, { count: number; correct: number; avg_score: number }>;
  weak_skills: string[];
  records: QuizRecordDTO[];
}

interface PracticeStatsDTO {
  total_practiced: number;
  total_correct: number;
  accuracy: number;
  by_type: Record<string, { practiced: number; correct: number; accuracy: number }>;
  by_skill: Array<{ skill: string; practiced: number; correct: number; accuracy: number }>;
  weak_skills: string[];
  weak_types: string[];
  recent_sessions: Array<{ session_id: string; date: string; score: number; count: number }>;
}

/** 单题答题。 */
export async function postPractice(payload: {
  questionId: number;
  questionType: string;
  userAnswer: string;
  generatedOptions?: string[] | null;
  skillName?: string | null;
  mode?: string;
  sessionId?: string | null;
}): Promise<PracticeResult> {
  const dto = await apiClient.post<PracticeResultDTO>("/api/interview/practice", {
    question_id: payload.questionId,
    question_type: payload.questionType,
    user_answer: payload.userAnswer,
    generated_options: payload.generatedOptions ?? null,
    skill_name: payload.skillName ?? null,
    mode: payload.mode ?? "single",
    session_id: payload.sessionId ?? null,
  });
  return {
    correct: dto.correct,
    score: dto.score,
    maxScore: dto.max_score,
    feedback: dto.feedback,
    correctAnswer: dto.correct_answer,
    outlineCovered: dto.outline_covered ?? [],
    outlineMissed: dto.outline_missed ?? [],
    recordId: dto.record_id,
  };
}

/** 开始小测验。 */
export async function startQuiz(payload: {
  skillName?: string | null;
  category?: string | null;
  count?: number;
}): Promise<QuizStart> {
  const dto = await apiClient.post<QuizStartDTO>("/api/interview/quiz/start", {
    skill_name: payload.skillName ?? null,
    category: payload.category ?? null,
    count: payload.count ?? 10,
  });
  return {
    sessionId: dto.session_id,
    questions: dto.questions.map((q) => ({
      id: q.id,
      question: q.question,
      questionType: q.question_type as QuestionType,
      options: q.options,
      skillName: q.skill_name,
      difficulty: q.difficulty,
    })),
    count: dto.count,
  };
}

/** 获取测验结果。 */
export async function getQuizResult(sessionId: string): Promise<QuizResult> {
  const dto = await apiClient.get<QuizResultDTO>(
    `/api/interview/quiz/${sessionId}/result`
  );
  return {
    sessionId: dto.session_id,
    totalScore: dto.total_score,
    count: dto.count,
    correctCount: dto.correct_count,
    byType: Object.fromEntries(
      Object.entries(dto.by_type).map(([k, v]) => [
        k,
        { count: v.count, correct: v.correct, avgScore: v.avg_score },
      ])
    ),
    weakSkills: dto.weak_skills,
    records: dto.records.map((r) => ({
      questionId: r.question_id,
      questionType: r.question_type as QuestionType,
      question: r.question,
      userAnswer: r.user_answer,
      correctAnswer: r.correct_answer,
      correct: r.correct,
      score: r.score,
      feedback: r.feedback,
    })),
  };
}

/** 获取练习统计。 */
export async function getPracticeStats(): Promise<PracticeStats> {
  const dto = await apiClient.get<PracticeStatsDTO>("/api/interview/practice/stats");
  return {
    totalPracticed: dto.total_practiced,
    totalCorrect: dto.total_correct,
    accuracy: dto.accuracy,
    byType: Object.fromEntries(
      Object.entries(dto.by_type).map(([k, v]) => [
        k,
        { practiced: v.practiced, correct: v.correct, accuracy: v.accuracy },
      ])
    ),
    bySkill: dto.by_skill.map((s) => ({
      skill: s.skill,
      practiced: s.practiced,
      correct: s.correct,
      accuracy: s.accuracy,
    })),
    weakSkills: dto.weak_skills,
    weakTypes: dto.weak_types,
    recentSessions: dto.recent_sessions.map((s) => ({
      sessionId: s.session_id,
      date: s.date,
      score: s.score,
      count: s.count,
    })),
  };
}
