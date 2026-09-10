/** Dashboard 聚合服务层。
 *
 * 职责：一次性获取 Dashboard 所需全部数据（Career / Skills / Tasks / AgentActivity /
 * JobHunt），供 Server Component（app/dashboard/page.tsx）调用。
 *
 * 设计原则：
 * - page.tsx 只调用 getDashboardData(role)，不直接编排业务逻辑
 * - 并行请求独立接口，减少瀑布延迟
 * - **雷达轴与匹配度口径与 /jobs 页同源**：都取自 `/api/job-hunt` 的赛道配置，
 *   避免两处数字对不上（原先 Dashboard 用全量技能求和、/jobs 用赛道 required 求和）
 * - **视角（role）只影响「展示哪个赛道」**，不改任何数据、不改 frozen 配置
 */

import type {
  ActiveTrack,
  AgentRunRecord,
  Career,
  Project,
  RadarAxis,
  Skill,
  TargetRole,
  Task,
  ViewRole,
  ViewRoleOption,
} from "@/types";
import { getAgentRuns } from "./agentService";
import { getCareer } from "./careerService";
import { getJobHuntBoard } from "./jobHuntService";
import { getSkills } from "./skillService";
import { getTasks } from "./taskService";
import { projectService } from "./projectService";
import { DEFAULT_VIEW_ROLE } from "@/lib/viewRole";

/** Dashboard 完整数据视图。 */
export interface DashboardData {
  // 前端 #4 修复：Career 未配置时后端返回 404，原实现会让整个 Promise.all reject，
  // 导致 Dashboard 显示"后端连接失败"（误报）。改为可空，未配置时渲染提示而非报错。
  career: Career | null;
  skills: Skill[]; // 全部技能（技能图谱明细 + Planner 输入）
  /** 当前视角 */
  viewRole: ViewRole;
  /** 切换器选项（由赛道配置派生，前端不硬编码赛道 key） */
  roleOptions: ViewRoleOption[];
  /** 当前视角对应的赛道（无数据时为 null） */
  activeTrack: ActiveTrack | null;
  /** 雷达轴 = 当前视角赛道的 required_skills */
  radarAxes: RadarAxis[];
  /** **本视角**的任务（按 activeTrack.key 过滤）—— 随角色看板变化 */
  tasks: Task[];
  /** 全部任务数（跨赛道），用于在卡片上显示 "本视角 N 项 / 全量 M 项" */
  tasksTotal: number;
  agentRuns: AgentRunRecord[]; // Agent Activity 面板
  projects: Project[]; // 项目进度
  daysLeft: number | null; // 距 offer 目标天数
}

/** 按视角挑选赛道。
 *
 * 关键：**不硬编码赛道 key**，全部从 `target_roles.py` 的配置语义派生 ——
 * 改配置即改视角，前端不重复一份真相。
 * - `jobhunt` → priority=主攻 的赛道（回退：第一个非冻结赛道 → 首个赛道）
 * - `embodied` → frozen=true 的长期赛道（回退：key="embodied"）
 */
function resolveTrack(roles: TargetRole[], role: ViewRole): TargetRole | null {
  if (!roles.length) return null;

  if (role === "embodied") {
    return roles.find((r) => r.frozen) ?? roles.find((r) => r.key === "embodied") ?? null;
  }

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

/** 构建切换器选项：固定 2 个角色（求职冲刺 / 具身智能），赛道由配置解析。 */
function buildRoleOptions(roles: TargetRole[]): ViewRoleOption[] {
  const jobhunt = resolveTrack(roles, "jobhunt");
  const embodied = resolveTrack(roles, "embodied");

  return [
    {
      role: "jobhunt",
      label: "求职冲刺",
      description: "对齐主攻赛道，服务于当前 offer 目标",
      available: jobhunt !== null,
      trackKey: jobhunt?.key ?? null,
      trackName: jobhunt?.name ?? null,
      matchPct: jobhunt?.matchPct ?? null,
      isLongTerm: false,
    },
    {
      role: "embodied",
      label: "具身智能",
      description: "长期目标视角，随时盘点与巩固，不占主线时间",
      available: embodied !== null,
      trackKey: embodied?.key ?? null,
      trackName: embodied?.name ?? null,
      matchPct: embodied?.matchPct ?? null,
      isLongTerm: true,
    },
  ];
}

/** 获取 Dashboard 全部数据。
 *
 * 数据流要点（2026-09-10 修复「任务没有跟随角色看板走」）：
 *   1. 先并行拉 Career / Skills / AgentRuns / Projects / JobHunt
 *   2. 从 JobHunt 的赛道配置解析出**当前视角的赛道**（这是唯一的真相来源，
 *      前端不硬编码赛道 key）
 *   3. 用该赛道 key **去后端按 track_key 过滤任务** —— 任务列表从此跟随视角；
 *      同时再拉一次全量用于显示 "本视角 N / 全量 M"（两次请求都是本地调用，
 *      代价可忽略，换来两个口径都准确）
 *
 * 容错：getCareer（404=未配置）与 getJobHuntBoard 都不阻断其余数据加载，
 * 避免因单接口异常误报"后端连接失败"。
 */
export async function getDashboardData(
  role: ViewRole = DEFAULT_VIEW_ROLE
): Promise<DashboardData> {
  const [career, skills, agentActivity, projects, board] = await Promise.all([
    getCareer().catch(() => null),
    getSkills(),
    getAgentRuns(undefined, 10),
    projectService.list(),
    getJobHuntBoard().catch(() => null),
  ]);

  const roles = board?.targetRoles ?? [];
  const picked = resolveTrack(roles, role);
  const trackKey = picked?.key ?? null;

  // 本视角任务（按赛道过滤）+ 全量任务（用于对比计数）
  const [tasks, allTasks] = await Promise.all([
    trackKey
      ? getTasks({ trackKey }).catch(() => [] as Task[])
      : getTasks().catch(() => [] as Task[]),
    getTasks().catch(() => [] as Task[]),
  ]);

  return {
    career,
    skills,
    viewRole: role,
    roleOptions: buildRoleOptions(roles),
    activeTrack: picked ? toActiveTrack(picked) : null,
    radarAxes: picked ? toRadarAxes(picked) : [],
    tasks,
    tasksTotal: allTasks.length,
    agentRuns: agentActivity.runs,
    projects,
    daysLeft: board?.daysLeft ?? null,
  };
}
