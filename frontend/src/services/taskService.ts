/** Task 服务层。
 *
 * 职责：调用后端 /api/tasks，做字段适配。
 * 统一返回 types/index.ts 的 Task 类型，避免组件层感知后端字段命名。
 * duration/objective/difficulty 可空，前端做默认值兜底。
 */

import { apiClient } from "@/lib/apiClient";
import type { Task, TaskStatus } from "@/types";

/** 后端 Task 响应原始结构（snake_case）。 */
export interface TaskDTO {
  id: number;
  title: string;
  objective: string | null;
  duration: number | null;
  difficulty: string | null;
  status: string;
  skill_name: string | null;
  acceptance: string[];
  resources: string[];
  project_id: number | null;
  milestone_id: number | null;
  track_key?: string | null;
  plan_day_id?: number | null;
}

/** 后端 → 前端转换。
 * - snake_case → camelCase
 * - int id → string id
 * - null objective/difficulty → undefined（对齐 Task 可选字段）
 * - null duration → 0
 * - status 字符串 → TaskStatus 联合类型
 *
 * 导出供其他 service 复用（如 planService 的今日任务），
 * 避免多处各写一份字段映射 —— 后端加字段时只改这里。
 */
export function toTask(dto: TaskDTO): Task {
  return {
    id: String(dto.id),
    title: dto.title,
    skill: dto.skill_name ?? "",
    duration: dto.duration ?? 0,
    acceptance: dto.acceptance ?? [],
    status: dto.status as TaskStatus,
    objective: dto.objective ?? undefined,
    difficulty: dto.difficulty ?? undefined,
    resources: dto.resources ?? [],
    projectId: dto.project_id != null ? String(dto.project_id) : null,
    milestoneId: dto.milestone_id != null ? String(dto.milestone_id) : null,
    trackKey: dto.track_key ?? null,
    planDayId: dto.plan_day_id != null ? String(dto.plan_day_id) : null,
  };
}

/** 任务查询条件。 */
export interface TaskQuery {
  /** 按项目过滤 */
  projectId?: string;
  /** 按赛道过滤（看板视角）—— 传了就只返回该赛道的任务 */
  trackKey?: string | null;
  /** 赛道过滤时是否一并带上未归类（历史 / 手写）任务 */
  includeUntracked?: boolean;
}

/** 获取任务列表。
 *
 * `trackKey` 用于让任务列表跟随看板视角：
 *   求职冲刺视角 → track_key=llm，具身视角 → track_key=embodied。
 * 不传则返回全量（"全部任务池"口径）。
 */
export async function getTasks(
  query: TaskQuery | string = {}
): Promise<Task[]> {
  // 兼容旧调用签名 getTasks(projectId?: string)
  const q: TaskQuery = typeof query === "string" ? { projectId: query } : query;

  const params = new URLSearchParams();
  if (q.projectId) params.set("project_id", q.projectId);
  if (q.trackKey) params.set("track_key", q.trackKey);
  if (q.includeUntracked) params.set("include_untracked", "true");

  const qs = params.toString();
  const dtos = await apiClient.get<TaskDTO[]>(`/api/tasks${qs ? `?${qs}` : ""}`);
  return dtos.map(toTask);
}

/** 更新任务状态（todo → doing → done）。 */
export async function updateTaskStatus(
  taskId: string,
  status: TaskStatus
): Promise<Task> {
  const dto = await apiClient.patch<TaskDTO>(`/api/tasks/${taskId}/status`, {
    status,
  });
  return toTask(dto);
}
