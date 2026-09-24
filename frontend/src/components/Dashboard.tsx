import type {
  ActiveTrack,
  AgentRunRecord,
  JobAppStatus,
  Project,
  Skill,
  SkillRadarData,
  Task,
} from "@/types";
import TopActionCard from "./TopActionCard";
import KpiCards from "./KpiCards";
import SkillRadarCard from "./SkillRadarCard";
import TaskList from "./TaskList";
import ProjectProgressCard from "./ProjectProgressCard";
import AgentActivityCard from "./AgentActivityCard";

/** Dashboard 布局容器 — 3 层优先级递减：
 *
 *   第 1 层：今天做什么？ → TopActionCard
 *   第 2 层：求职进展如何？ → KpiCards + TaskList + 投递摘要
 *   第 3 层：能力盘点 → 雷达图 + 项目进度 + Agent 活动
 */
type Props = {
  skills: Skill[];
  activeTrack: ActiveTrack | null;
  /** 技能雷达数据（形态由当前模式决定，见 services/skillRadarService）。 */
  skillRadar: SkillRadarData;
  defaultScopeTasks: Task[];
  frozenExcludedTasks: number;
  unclassifiedTasks: number;
  taskScopeReason: string | null;
  agentRuns: AgentRunRecord[];
  projects: Project[];
  daysLeft: number | null;
  /** 投递漏斗各阶段数量。 */
  applicationCounts?: Record<JobAppStatus, number>;
};

export default function Dashboard({
  skills,
  activeTrack,
  skillRadar,
  defaultScopeTasks,
  frozenExcludedTasks,
  unclassifiedTasks,
  taskScopeReason,
  agentRuns,
  projects,
  daysLeft,
  applicationCounts,
}: Props) {
  const readiness = activeTrack?.matchPct ?? 0;

  const displayFilter = activeTrack
    ? {
        trackKey: activeTrack.key,
        trackName: activeTrack.name,
        isFrozen: activeTrack.frozen ?? false,
      }
    : null;

  return (
    <div className="flex flex-1 flex-col">
      <div
        className="flex flex-col"
        style={{
          gap: "var(--spacing-lg)",
          padding: "36px clamp(20px, 8vw, 120px) 48px",
        }}
      >
        {/* ═══════ 第 1 层：今天做什么 ═══════ */}
        <TopActionCard
          daysLeft={daysLeft}
          activeTrack={activeTrack}
          tasks={defaultScopeTasks}
        />

        {/* ═══════ 第 2 层：求职进展 ═══════ */}
        <KpiCards
          tasks={defaultScopeTasks}
          excludedFrozen={frozenExcludedTasks}
          unclassified={unclassifiedTasks}
          agentRuns={agentRuns}
          readiness={readiness}
          readinessLabel="岗位匹配度"
          readinessSub={
            activeTrack
              ? `推进度按「${activeTrack.name}」的 ${activeTrack.skillCount} 项硬性要求技能计算；` +
                `严格达标 ${activeTrack.strictPct ?? "—"}%（${activeTrack.qualifiedCount ?? "—"}/${activeTrack.skillCount} 项 level≥4）`
              : "按当前赛道硬性要求技能计算"
          }
          applicationCounts={applicationCounts}
        />

        <div className="flex" style={{ gap: "var(--spacing-lg)" }}>
          <TaskList
            tasks={defaultScopeTasks}
            viewFilter={displayFilter}
            excludedFrozen={frozenExcludedTasks}
            unclassified={unclassifiedTasks}
            scopeReason={taskScopeReason}
          />
          <ProjectProgressCard projects={projects} />
        </div>

        {/* ═══════ 第 3 层：能力盘点 ═══════ */}
        <SkillRadarCard data={skillRadar} />

        <AgentActivityCard runs={agentRuns} limit={5} />

        {/* Footer */}
        <div className="flex justify-center" style={{ paddingTop: 8 }}>
          <span className="text-xs font-medium" style={{ color: "var(--text-muted)" }}>
            Keep simple · Build fast · Use AI agents
          </span>
        </div>
      </div>
    </div>
  );
}
