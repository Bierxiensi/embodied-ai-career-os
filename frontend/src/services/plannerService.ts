/** Planner 服务层。
 *
 * 职责：调用后端 /api/planner/generate，传入技能缺口生成任务。
 * 后端会将生成的任务持久化到 tasks 表，并记录 agent_runs。
 */

import { apiClient } from "@/lib/apiClient";
import type { PlannerResult, PlannerSkillInput } from "@/types";

/** 后端 Planner 响应原始结构（snake_case task_id）。 */
interface PlannerResultDTO {
  title: string;
  skill: string;
  objective: string | null;
  duration: number;
  difficulty: string | null;
  acceptance: string[];
  resources: string[];
  status: string;
  task_id: number | null;
}

/** Planner 请求参数。 */
export interface PlannerParams {
  availableMinutes: number;
  targetRole?: string;
  skills: PlannerSkillInput[];
  energyLevel?: "low" | "normal" | "high";
  currentFocus?: string | null;
  persist?: boolean;
}

/** 调用 Planner Agent 生成任务。 */
export async function generateTask(params: PlannerParams): Promise<PlannerResult> {
  const dto = await apiClient.post<PlannerResultDTO>("/api/planner/generate", {
    available_minutes: params.availableMinutes,
    target_role: params.targetRole ?? "Robot AI Engineer",
    skills: params.skills,
    energy_level: params.energyLevel ?? "normal",
    current_focus: params.currentFocus ?? null,
    persist: params.persist ?? true,
  });

  return {
    title: dto.title,
    skill: dto.skill,
    objective: dto.objective,
    duration: dto.duration,
    difficulty: dto.difficulty,
    acceptance: dto.acceptance,
    resources: dto.resources,
    status: dto.status,
    taskId: dto.task_id,
  };
}
