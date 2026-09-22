/** Task 服务层。
 *
 * 职责：调用后端 /api/tasks，做字段适配。
 * 统一返回 types/index.ts 的 Task 类型，避免组件层感知后端字段命名。
 * duration/objective/difficulty 可空，前端做默认值兜底。
 */

import { apiClient } from "@/lib/apiClient";
import type { Task, TaskScopeMode, TaskStatus } from "@/types";

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
  /** 按赛道过滤 —— **显式**的赛道查询（例如"查看某赛道的全部任务"）。
   * 这是查询条件，不代表"当前看哪个视角"：
   * **禁止**用展示视角推导出它去请求任务列表（Milestone B 契约；
   * ViewRole 概念已于 2026-09-22 删除）。 */
  trackKey?: string | null;
  /** 赛道过滤时是否一并带上未归类（历史 / 手写）任务 */
  includeUntracked?: boolean;
  /** 范围口径：
   * - `all`（默认）：原始全量，不施加阶段口径
   * - `current_mode`：平台默认视图口径，由当前 CareerMode 决定，与 /jobs、/today 同源
   * 只随 CareerMode 变化，不得由展示视角推导。 */
  scope?: TaskScopeMode;
}

/** 获取任务列表。
 *
 * `scope` 决定"要哪个范围"（见 TaskScopeMode）；不传即原始全量。
 * `trackKey` 是显式的赛道查询条件，与视角无关。
 *
 * 历史修正（2026-09-10 的注释曾写"trackKey 用于让任务列表跟随看板视角：
 * 求职冲刺 → llm、具身 → embodied"）：那句说明把**展示视角**当成了**任务策略**，
 * 已被 Milestone B 收尾推翻。任务范围只能由 CareerMode 决定；
 * 视角切换不得改变这里的请求参数（见 docs/PRD_CAREER_OS_MODES.md §5 F5）。
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
  if (q.scope && q.scope !== "all") params.set("scope", q.scope);

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
