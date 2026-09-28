/** Planner 服务层。
 *
 * 职责：调用后端 /api/planner/generate，传入技能缺口生成任务。
 * 后端会将生成的任务持久化到 tasks 表，并记录 agent_runs。
 *
 * 2026-09-10：请求新增 `track_key`（当前视角赛道），响应新增决策细节
 * （选中的技能、缺口、新建/复用、解释文案）—— 前端据此渲染结果卡。
 */

import { apiClient } from "@/lib/apiClient";
import type { PlannerResult, PlannerSkillInput } from "@/types";

/** 后端 Planner 响应原始结构（snake_case）。 */
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
  track_key: string | null;
  track_name: string | null;
  track_frozen: boolean;
  skill_level: number | null;
  skill_target: number | null;
  gap: number | null;
  reused: boolean;
  reason: string;
}

/** Planner 请求参数。 */
export interface PlannerParams {
  availableMinutes: number;
  targetRole?: string;
  /** 当前视角赛道（llm / vlm / ai-algo / embodied）。
   * 后端据此把候选技能收敛到该赛道的硬性要求 —— 不传则用「主攻」赛道。 */
  trackKey?: string | null;
  skills: PlannerSkillInput[];
  energyLevel?: "low" | "normal" | "high";
  currentFocus?: string | null;
  persist?: boolean;
  /** 任务生成器：rule（默认，毫秒级可复现）| llm（5-10s，AI 生成）。
   * 2026-09-24 Y10：显式开关，不改后端默认。 */
  generator?: "rule" | "llm";
}

/** 调用 Planner Agent 生成任务。 */
export async function generateTask(params: PlannerParams): Promise<PlannerResult> {
  const body: Record<string, unknown> = {
    available_minutes: params.availableMinutes,
    generator: params.generator ?? "rule",
    skills: params.skills,
    energy_level: params.energyLevel ?? "normal",
    current_focus: params.currentFocus ?? null,
    persist: params.persist ?? true,
  };
  // 仅在显式指定时才传 target_role，否则交给后端按 target_roles 配置取「主攻」赛道。
  // 原实现前端写死 "Robot AI Engineer"（具身方向），与 llm 主攻战略冲突。
  if (params.targetRole) {
    body.target_role = params.targetRole;
  }
  // 视角赛道：显式传 null 也有意义（"不指定，由后端取主攻"），故用 !== undefined 判断
  if (params.trackKey !== undefined) {
    body.track_key = params.trackKey;
  }

  const dto = await apiClient.post<PlannerResultDTO>("/api/planner/generate", body);

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
    trackKey: dto.track_key ?? null,
    trackName: dto.track_name ?? null,
    trackFrozen: Boolean(dto.track_frozen),
    skillLevel: dto.skill_level ?? null,
    skillTarget: dto.skill_target ?? null,
    gap: dto.gap ?? null,
    reused: Boolean(dto.reused),
    reason: dto.reason ?? "",
  };
}
