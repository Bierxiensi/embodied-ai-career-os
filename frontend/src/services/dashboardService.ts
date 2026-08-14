/** Dashboard 聚合服务层。
 *
 * 职责：一次性获取 Dashboard 所需全部数据（Career / Skills / Tasks / AgentActivity），
 * 供 Server Component（app/dashboard/page.tsx）调用。
 *
 * 设计原则（遵循用户调整5）：
 * - page.tsx 只调用 getDashboardData()，不直接编排业务逻辑
 * - 并行请求四个独立接口，减少瀑布延迟
 * - radarSkills 由本地过滤得出，避免重复请求 /api/skills
 */

import type { AgentRunRecord, Career, Project, Skill, Task } from "@/types";
import { getAgentRuns } from "./agentService";
import { getCareer } from "./careerService";
import { filterRadarSkills, getSkills } from "./skillService";
import { getTasks } from "./taskService";
import { projectService } from "./projectService";

/** Dashboard 完整数据视图。 */
export interface DashboardData {
  // 前端 #4 修复：Career 未配置时后端返回 404，原实现会让整个 Promise.all reject，
  // 导致 Dashboard 显示"后端连接失败"（误报）。改为可空，未配置时渲染提示而非报错。
  career: Career | null;
  skills: Skill[]; // 全部技能（SkillCard 明细 + Planner 输入）
  radarSkills: Skill[]; // 核心能力子集（雷达图）
  tasks: Task[];
  agentRuns: AgentRunRecord[]; // Phase 2 Day6：Agent Activity 面板
  projects: Project[]; // V2: 项目进度
}

/** 获取 Dashboard 全部数据。
 *
 * 并行请求 Career / Skills / Tasks / AgentRuns / Projects 五个接口，
 * skills 复用一次请求结果本地过滤出 radarSkills。
 * Agent Activity 取最近 10 条，避免面板过长。
 *
 * 前端 #4 修复：getCareer 单独容错——未配置职业目标（404）时返回 null，
 * 不阻断其余数据加载，避免误报"后端连接失败"。
 */
export async function getDashboardData(): Promise<DashboardData> {
  const [career, skills, tasks, agentActivity, projects] = await Promise.all([
    getCareer().catch(() => null),
    getSkills(),
    getTasks(),
    getAgentRuns(undefined, 10),
    projectService.list(),
  ]);

  return {
    career,
    skills,
    radarSkills: filterRadarSkills(skills),
    tasks,
    agentRuns: agentActivity.runs,
    projects,
  };
}
