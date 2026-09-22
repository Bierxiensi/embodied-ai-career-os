/** Dashboard 聚合服务层。
 *
 * 职责：一次性获取 Dashboard 所需全部数据，供 Server Component 调用。
 * 数据流：并行拉取 Career / Skills / AgentRuns / Projects / JobHunt，
 * 任务只请求一次（CareerMode 口径），与 /jobs、/today 同源。
 *
 * 边界说明：本服务不解析也不消费 ViewRole —— ViewRole 仅是展示视角（cookie/?role=），
 * 禁止影响任务请求参数、数据范围与统计；数据范围一律由 CareerMode（scope: current_mode）决定。
 */

import type {
  ActiveTrack,
  AgentRunRecord,
  Career,
  JobAppStatus,
  Project,
  RadarAxis,
  Skill,
  TargetRole,
  Task,
} from "@/types";
import { getAgentRuns } from "./agentService";
import { getCareer } from "./careerService";
import { getJobHuntBoard } from "./jobHuntService";
import { getSkills } from "./skillService";
import { getTasks } from "./taskService";
import { projectService } from "./projectService";

/** Dashboard 完整数据视图。 */
export interface DashboardData {
  career: Career | null;
  skills: Skill[];
  activeTrack: ActiveTrack | null;
  radarAxes: RadarAxis[];
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

function toRadarAxes(t: TargetRole): RadarAxis[] {
  return t.skills.map((s) => ({
    name: s.name,
    current: s.level,
    required: s.required,
    gap: s.gap,
  }));
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
  const [career, skills, agentActivity, projects, board, defaultScopeTasks] =
    await Promise.all([
      getCareer().catch(() => null),
      getSkills(),
      getAgentRuns(undefined, 10),
      projectService.list(),
      getJobHuntBoard().catch(() => null),
      getTasks({ scope: "current_mode" }).catch(() => [] as Task[]),
    ]);

  const roles = board?.targetRoles ?? [];
  const picked = resolvePrimaryTrack(roles);

  return {
    career,
    skills,
    activeTrack: picked ? toActiveTrack(picked) : null,
    radarAxes: picked ? toRadarAxes(picked) : [],
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
