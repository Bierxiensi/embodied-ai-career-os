/** Dashboard 聚合服务层。
 *
 * 职责：一次性获取 Dashboard 所需全部数据，供 Server Component 调用。
 * 数据流：并行拉取 Career / Skills / AgentRuns / Projects / JobHunt / 模式 / 六域，
 * 任务只请求一次（CareerMode 口径），与 /jobs、/today 同源。
 *
 * 边界说明：任务的数据范围一律由 CareerMode（scope: current_mode）决定。
 * 历史上的 ViewRole（展示视角，cookie/?role=）已于 2026-09-22 整体删除
 * （lib/viewRole.ts 与类型移除），本服务不存在也不允许存在视角解析逻辑。
 *
 * Phase 3：技能雷达不再由本服务"直接给轴"，而是给出**已适配好的**
 * `SkillRadarData` —— 轴是岗位技能还是能力六域，取决于当前模式。
 * 取舍逻辑收在 `services/skillRadarService.buildSkillRadar`（唯一实现），
 * 与 /today 落地页共用，避免两页对"当前该看什么"给出不同答案。
 */

import type {
  ActiveTrack,
  AgentRunRecord,
  Career,
  JobAppStatus,
  Project,
  Skill,
  SkillRadarData,
  TargetRole,
  Task,
} from "@/types";
import { getAgentRuns } from "./agentService";
import { getCareer } from "./careerService";
import { getCareerModeOverview } from "./careerModeService";
import { getJobHuntBoard } from "./jobHuntService";
import { getSkillDomains, getSkills } from "./skillService";
import { buildSkillRadar } from "./skillRadarService";
import { getTasks } from "./taskService";
import { projectService } from "./projectService";

/** Dashboard 完整数据视图。 */
export interface DashboardData {
  career: Career | null;
  skills: Skill[];
  activeTrack: ActiveTrack | null;
  /** 技能雷达数据（形态由当前模式决定：R1 岗位对齐 / R2 域聚合）。 */
  skillRadar: SkillRadarData;
  defaultScopeTasks: Task[];
  frozenExcludedTasks: number;
  unclassifiedTasks: number;
  taskScopeReason: string | null;
  agentRuns: AgentRunRecord[];
  projects: Project[];
  daysLeft: number | null;
  applicationCounts: Record<JobAppStatus, number>;
}

/** 挑选主攻赛道用于展示。 */
function resolvePrimaryTrack(roles: TargetRole[]): TargetRole | null {
  if (!roles.length) return null;
  return (
    roles.find((r) => r.priority === "主攻") ??
    roles.find((r) => !r.frozen) ??
    roles[0] ??
    null
  );
}

function toActiveTrack(t: TargetRole): ActiveTrack {
  return {
    key: t.key,
    name: t.name,
    priority: t.priority,
    matchPct: t.matchPct,
    strictPct: t.strictPct,
    qualifiedCount: t.qualifiedCount,
    frozen: t.frozen,
    skillCount: t.skills.length,
    gapCount: t.skills.filter((s) => s.gap > 0).length,
  };
}

const EMPTY_COUNTS: Record<JobAppStatus, number> = {
  applied: 0,
  screening: 0,
  interview: 0,
  offer: 0,
  rejected: 0,
};

/** 获取 Dashboard 全部数据。 */
export async function getDashboardData(): Promise<DashboardData> {
  const [
    career,
    skills,
    agentActivity,
    projects,
    board,
    defaultScopeTasks,
    modeOverview,
    domains,
  ] = await Promise.all([
    getCareer().catch(() => null),
    getSkills(),
    getAgentRuns(undefined, 10),
    projectService.list(),
    getJobHuntBoard().catch(() => null),
    getTasks({ scope: "current_mode" }).catch(() => [] as Task[]),
    getCareerModeOverview().catch(() => null),
    getSkillDomains().catch(() => null),
  ]);

  const roles = board?.targetRoles ?? [];
  const picked = resolvePrimaryTrack(roles);

  return {
    career,
    skills,
    activeTrack: picked ? toActiveTrack(picked) : null,
    skillRadar: buildSkillRadar({
      modeKey: modeOverview?.current.key ?? null,
      targetRoles: board?.targetRoles ?? null,
      domains,
    }),
    defaultScopeTasks,
    frozenExcludedTasks: board?.tasks.frozenExcluded ?? 0,
    unclassifiedTasks: board?.tasks.unclassified ?? 0,
    taskScopeReason: board?.tasks.scope.scopeReason || null,
    agentRuns: agentActivity.runs,
    projects,
    daysLeft: board?.daysLeft ?? null,
    applicationCounts: board?.applications.byStatus ?? EMPTY_COUNTS,
  };
}

