/** Task 服务层。
 *
 * 职责：调用后端 /api/tasks，做字段适配。
 * 统一返回 types/index.ts 的 Task 类型，避免组件层感知后端字段命名。
 * duration/objective/difficulty 可空，前端做默认值兜底。
 */

import { apiClient } from "@/lib/apiClient";
import type { Task, TaskStatus } from "@/types";

/** 后端 Task 响应原始结构（snake_case）。 */
interface TaskDTO {
  id: number;
  title: string;
  objective: string | null;
  duration: number | null;
  difficulty: string | null;
  status: string;
  skill_name: string | null;
  acceptance: string[];
  resources: string[];
}

/** 后端 → 前端转换。
 * - snake_case → camelCase
 * - int id → string id
 * - null objective/difficulty → undefined（对齐 Task 可选字段）
 * - null duration → 0
 * - status 字符串 → TaskStatus 联合类型
 */
function toTask(dto: TaskDTO): Task {
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
  };
}

/** 获取任务列表。 */
export async function getTasks(): Promise<Task[]> {
  const dtos = await apiClient.get<TaskDTO[]>("/api/tasks");
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
