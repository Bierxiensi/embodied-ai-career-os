import type { AgentRunRecord, Career, Project, Skill, Task } from "@/types";
import GlobalNav from "./GlobalNav";
import SubNav from "./SubNav";
import KpiCards from "./KpiCards";
import SkillRadarCard from "./SkillRadarCard";
import QuickActions from "./QuickActions";
import TodayTasks from "./TodayTasks";
import ProjectProgressCard from "./ProjectProgressCard";
import AgentActivityCard from "./AgentActivityCard";

/** Dashboard 布局容器 — 匹配 Ardot 设计稿。
 *
 * 布局结构：
 *   GlobalNav (黑色顶栏)
 *   SubNav (标题 + 日期 + 生成今日任务)
 *   content-container
 *     ├── PageHeader
 *     ├── KpiCards (4列)
 *     ├── main-grid-row1 (雷达图 690px + 快捷操作 flex-1)
 *     ├── main-grid-row2 (今日任务 690px + 项目进度 flex-1)
 *     ├── AgentActivityCard
 *     └── Footer
 */
type Props = {
  career: Career | null;
  skills: Skill[];
  radarSkills: Skill[];
  tasks: Task[];
  agentRuns: AgentRunRecord[];
  projects: Project[];
};

export default function Dashboard({
  career,
  skills,
  radarSkills,
  tasks,
  agentRuns,
  projects,
}: Props) {
  return (
    <div className="flex min-h-screen flex-col" style={{ background: "var(--color-canvas)" }}>
      {/* Global Nav */}
      <GlobalNav />

      {/* Sub Nav */}
      <SubNav skills={skills} />

      {/* Content Container */}
      <div
        className="flex flex-col"
        style={{
          gap: "var(--spacing-lg)",
          padding: "36px clamp(20px, 8vw, 120px) 48px",
        }}
      >
        {/* Page Header */}
        <div className="flex flex-col" style={{ gap: 8 }}>
          <span
            className="text-xs font-semibold uppercase"
            style={{ color: "var(--color-ink-48)", letterSpacing: "0.04em" }}
          >
            PHASE 2 · WEEK 1 · MULTI-AGENT
          </span>
          <h1
            className="font-semibold"
            style={{ fontSize: 40, color: "var(--color-ink)", letterSpacing: "-0.02em" }}
          >
            Embodied AI Career OS
          </h1>
          <p className="text-[17px]" style={{ color: "var(--color-ink-48)" }}>
            AI 驱动的具身智能职业成长操作系统 · 今日聚焦 VLA 与 Sim2Real
          </p>
        </div>

        {/* KPI Cards Row */}
        <KpiCards
          career={career}
          tasks={tasks}
          agentRuns={agentRuns}
          readiness={computeReadiness(radarSkills)}
        />

        {/* Main Grid Row 1: Radar + Quick Actions */}
        <div className="flex" style={{ gap: "var(--spacing-lg)" }}>
          <SkillRadarCard skills={radarSkills} />
          <div className="flex flex-1 flex-col" style={{ gap: "var(--spacing-lg)" }}>
            <QuickActions skills={radarSkills} />
          </div>
        </div>

        {/* Main Grid Row 2: Tasks + Projects */}
        <div className="flex" style={{ gap: "var(--spacing-lg)" }}>
          <TodayTasks tasks={tasks} />
          <ProjectProgressCard projects={projects} />
        </div>

        {/* Agent Activity */}
        <AgentActivityCard runs={agentRuns} limit={5} />

        {/* Footer */}
        <div className="flex justify-center" style={{ paddingTop: 8 }}>
          <span className="text-xs font-medium" style={{ color: "#A1A1AA" }}>
            Keep simple · Build fast · Use AI agents
          </span>
        </div>
      </div>
    </div>
  );
}

/** 计算 AI 就绪度百分比。 */
function computeReadiness(skills: Skill[]): number {
  const totalCurrent = skills.reduce((s, sk) => s + sk.level, 0);
  const totalTarget = skills.reduce((s, sk) => s + sk.targetLevel, 0);
  return totalTarget > 0 ? Math.round((totalCurrent / totalTarget) * 100) : 0;
}
