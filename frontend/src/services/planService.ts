/** 课程计划服务层（30 天施工执行台）。
 *
 * 对应后端 /api/plan 系列端点：
 *   GET    /api/plan                30 天课程脊梁
 *   GET    /api/plan/today          今日施工单（可用 ?day= 指定课程日）
 *   POST   /api/plan/artifacts      勾选一件四件套产出
 *   DELETE /api/plan/artifacts/{id} 取消勾选
 *
 * 与其它 service 同一套约定：后端 snake_case → 前端 camelCase，int id → string id。
 */

import { apiClient } from "@/lib/apiClient";
import type {
  ArtifactKind,
  DayArtifact,
  DayProgressStatus,
  LedgerItem,
  PlanDay,
  PlanDayStatus,
  PlanOverview,
  TodayView,
} from "@/types";
import { toTask, type TaskDTO } from "./taskService";
import {
  toScopeSummary,
  toScopedTaskRef,
  type ScopedTaskRefDTO,
  type TaskScopeDTO,
} from "./taskScope";

/** 后端 PlanDay 原始结构。 */
interface PlanDayDTO {
  id: number;
  seq: number;
  phase: number;
  phase_name: string;
  title: string;
  theme: string;
  objectives: string[];
  acceptance: string[];
  interview_topics: string[];
  resources: string[];
  est_minutes: number;
  track_key: string;
}

/** 后端 DayArtifact 原始结构。 */
interface ArtifactDTO {
  id: number;
  plan_day_id: number;
  kind: string;
  title: string | null;
  url: string | null;
  auto_verified: boolean;
  note: string | null;
  created_at: string;
}

/** 后端 TodayView 原始结构。 */
interface TodayDTO {
  day: PlanDayDTO;
  day_index: number;
  total_days: number;
  calendar_days_elapsed: number;
  sprint_start: string;
  is_before_start: boolean;
  is_after_end: boolean;
  tasks: TaskDTO[];
  completed_tasks: number;
  artifacts: ArtifactDTO[];
  artifact_status: Record<string, number>;
  /** P2：当日题库条数（>= QUESTIONS_MIN_PER_DAY 时 questions 轴自动判定为已交） */
  questions_from_bank: number;
  missing_kinds: string[];
  all_done: boolean;
  ledger: { key: string; label: string; done: number; target: number }[];
  /** Milestone B：与 /api/job-hunt 同源的任务赛道口径（可选，向后兼容） */
  task_scope?: TaskScopeDTO | null;
  excluded_tasks?: ScopedTaskRefDTO[];
}

function toPlanDay(dto: PlanDayDTO): PlanDay {
  return {
    id: String(dto.id),
    seq: dto.seq,
    phase: dto.phase,
    phaseName: dto.phase_name,
    title: dto.title,
    theme: dto.theme,
    objectives: dto.objectives ?? [],
    acceptance: dto.acceptance ?? [],
    interviewTopics: dto.interview_topics ?? [],
    resources: dto.resources ?? [],
    estMinutes: dto.est_minutes || 360,
    trackKey: dto.track_key || "llm",
  };
}

function toArtifact(dto: ArtifactDTO): DayArtifact {
  return {
    id: String(dto.id),
    planDayId: String(dto.plan_day_id),
    kind: dto.kind as ArtifactKind,
    title: dto.title ?? undefined,
    url: dto.url ?? undefined,
    autoVerified: dto.auto_verified,
    note: dto.note ?? undefined,
    createdAt: dto.created_at,
  };
}

function toToday(dto: TodayDTO): TodayView {
  return {
    day: toPlanDay(dto.day),
    dayIndex: dto.day_index,
    totalDays: dto.total_days,
    calendarDaysElapsed: dto.calendar_days_elapsed,
    sprintStart: dto.sprint_start,
    isBeforeStart: dto.is_before_start,
    isAfterEnd: dto.is_after_end,
    tasks: (dto.tasks ?? []).map(toTask),
    completedTasks: dto.completed_tasks ?? 0,
    artifacts: (dto.artifacts ?? []).map(toArtifact),
    artifactStatus: dto.artifact_status ?? {},
    questionsFromBank: dto.questions_from_bank ?? 0,
    missingKinds: (dto.missing_kinds ?? []) as ArtifactKind[],
    allDone: dto.all_done,
    ledger: (dto.ledger ?? []) as LedgerItem[],
    // 口径与"被排除任务"：转换逻辑与 /api/job-hunt 共用 services/taskScope.ts，
    // 不在这里各写一遍（后端也只有一份判定，前端也只有一份搬运）。
    taskScope: dto.task_scope ? toScopeSummary(dto.task_scope) : null,
    excludedTasks: (dto.excluded_tasks ?? []).map(toScopedTaskRef),
  };
}

/** 获取今日施工单。
 *
 * `day` 可显式指定课程日（回看 / 预看）；不传则后端按日历推导。
 */
export async function getToday(day?: number): Promise<TodayView> {
  const qs = day !== undefined ? `?day=${day}` : "";
  const dto = await apiClient.get<TodayDTO>(`/api/plan/today${qs}`);
  return toToday(dto);
}

/** 获取 30 天课程脊梁（施工总览页用）。 */
export async function getPlanDays(): Promise<PlanDay[]> {
  const dtos = await apiClient.get<PlanDayDTO[]>("/api/plan");
  return dtos.map(toPlanDay);
}

/** 勾选一件产出。 */
export async function createArtifact(payload: {
  planDayId: string;
  kind: ArtifactKind;
  title?: string;
  url?: string;
  note?: string;
}): Promise<DayArtifact> {
  const dto = await apiClient.post<ArtifactDTO>("/api/plan/artifacts", {
    plan_day_id: Number(payload.planDayId),
    kind: payload.kind,
    title: payload.title ?? null,
    url: payload.url ?? null,
    note: payload.note ?? null,
  });
  return toArtifact(dto);
}

/** 取消勾选（删除一条产出记录）。 */
export async function deleteArtifact(artifactId: string): Promise<void> {
  await apiClient.delete<{ id: number }>(`/api/plan/artifacts/${artifactId}`);
}

// ===== P1：30 天总览 + 滑期决策 =====

/** 后端 PlanDayStatus 原始结构。 */
interface PlanDayStatusDTO {
  seq: number;
  plan_day_id: number;
  phase: number;
  phase_name: string;
  title: string;
  theme: string;
  track_key: string;
  est_minutes: number;
  status: string;
  full_artifacts: boolean;
  is_missed: boolean;
  deviation_note: string | null;
}

/** 后端 PlanOverview 原始结构。 */
interface PlanOverviewDTO {
  day_index: number;
  total_days: number;
  sprint_start: string;
  sprint_end: string;
  calendar_days_elapsed: number;
  is_before_start: boolean;
  is_after_end: boolean;
  behind: number;
  completed_days: number;
  days: PlanDayStatusDTO[];
}

function toDayStatus(d: PlanDayStatusDTO): PlanDayStatus {
  return {
    seq: d.seq,
    planDayId: String(d.plan_day_id),
    phase: d.phase,
    phaseName: d.phase_name,
    title: d.title,
    theme: d.theme,
    trackKey: d.track_key || "llm",
    estMinutes: d.est_minutes || 360,
    status: d.status as DayProgressStatus,
    fullArtifacts: d.full_artifacts,
    isMissed: d.is_missed,
    deviationNote: d.deviation_note ?? undefined,
  };
}

function toPlanOverview(d: PlanOverviewDTO): PlanOverview {
  return {
    dayIndex: d.day_index,
    totalDays: d.total_days,
    sprintStart: d.sprint_start,
    sprintEnd: d.sprint_end,
    calendarDaysElapsed: d.calendar_days_elapsed,
    isBeforeStart: d.is_before_start,
    isAfterEnd: d.is_after_end,
    behind: d.behind,
    completedDays: d.completed_days,
    days: (d.days ?? []).map(toDayStatus),
  };
}

/** 获取 30 天课程总览（课程进度 vs 日历进度）。 */
export async function getPlanOverview(day?: number): Promise<PlanOverview> {
  const qs = day !== undefined ? `?day=${day}` : "";
  const dto = await apiClient.get<PlanOverviewDTO>(`/api/plan/overview${qs}`);
  return toPlanOverview(dto);
}

/** 手动记录一天的执行决策（压缩 / 顺延 / 放弃 / 完成）。 */
export async function setDayProgress(payload: {
  planDayId: string;
  status: DayProgressStatus;
  deviationNote?: string;
  actualMinutes?: number;
}): Promise<void> {
  await apiClient.post<unknown>("/api/plan/progress", {
    plan_day_id: Number(payload.planDayId),
    status: payload.status,
    deviation_note: payload.deviationNote ?? null,
    actual_minutes: payload.actualMinutes ?? null,
  });
}
