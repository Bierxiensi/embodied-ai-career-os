import type {
  ActiveTrack,
  AgentRunRecord,
  Career,
  Project,
  RadarAxis,
  Skill,
  Task,
  ViewRole,
  ViewRoleOption,
} from "@/types";
import SubNav from "./SubNav";
import KpiCards from "./KpiCards";
import SkillRadarCard from "./SkillRadarCard";
import QuickActions from "./QuickActions";
import TodayTasks from "./TodayTasks";
import ProjectProgressCard from "./ProjectProgressCard";
import AgentActivityCard from "./AgentActivityCard";
import RoleSwitcher from "./RoleSwitcher";

/** Dashboard 布局容器 — 匹配 Ardot 设计稿。
 *
 * 布局结构：
 *   GlobalNav (黑色顶栏，由 app/layout.tsx 统一渲染)
 *   SubNav (标题 + 日期 + 生成今日任务)
 *   content-container
 *     ├── PageHeader（含视角切换器）
 *     ├── KpiCards (4列)
 *     ├── main-grid-row1 (雷达图 690px + 快捷操作 flex-1)
 *     ├── main-grid-row2 (任务 690px + 项目进度 flex-1)
 *     ├── AgentActivityCard
 *     └── Footer
 *
 * 叙事口径：本页是「求职作战 / 具身成长」双视角看板。标题、雷达轴、匹配度、
 * 就绪度标签、**任务列表**全部由 `viewRole` + `activeTrack` 驱动
 * （赛道配置来自 /api/job-hunt），页面不硬编码任何赛道名，
 * 也不再残留 "今日聚焦 VLA / Sim2Real" 这类旧叙事。
 */
type Props = {
  career: Career | null;
  skills: Skill[];
  /** 当前视角（求职冲刺 / 具身智能） */
  viewRole: ViewRole;
  /** 切换器选项 */
  roleOptions: ViewRoleOption[];
  /** 当前视角对应的赛道 */
  activeTrack: ActiveTrack | null;
  radarAxes: RadarAxis[];
  /** 本视角的任务（按 activeTrack.key 过滤） */
  tasks: Task[];
  /** 全量任务数（跨赛道），用于任务卡片的对比计数 */
  tasksTotal: number;
  agentRuns: AgentRunRecord[];
  projects: Project[];
  daysLeft: number | null;
};

export default function Dashboard({
  career,
  skills,
  viewRole,
  roleOptions,
  activeTrack,
  radarAxes,
  tasks,
  tasksTotal,
  agentRuns,
  projects,
  daysLeft,
}: Props) {
  const isEmbodied = viewRole === "embodied";

  // 就绪度 = 当前视角赛道的匹配度（与 /jobs 页同一口径，避免两处数字对不上）
  const readiness = activeTrack?.matchPct ?? 0;

  const eyebrow = isEmbodied ? "长期视角 · EMBODIED" : "求职作战 · MULTI-AGENT";
  const heading = isEmbodied ? "具身智能成长看板" : "求职作战看板";
  const subtitle = isEmbodied
    ? `长期目标视角 · 对齐 ${activeTrack?.name ?? "具身赛道"} · 随时盘点与巩固，不占冲刺期主线时间`
    : `AI 驱动的求职作战看板 · 主攻 ${activeTrack?.name ?? "目标岗位"}${
        daysLeft !== null ? ` · 距 offer 目标 ${daysLeft} 天` : ""
      }`;

  return (
    <div className="flex flex-1 flex-col">
      {/* Sub Nav（顶栏 GlobalNav 已在 app/layout.tsx 统一渲染） */}
      <SubNav skills={skills} trackKey={activeTrack?.key ?? null} trackName={activeTrack?.name ?? null} />

      {/* Content Container */}
      <div
        className="flex flex-col"
        style={{
          gap: "var(--spacing-lg)",
          padding: "36px clamp(20px, 8vw, 120px) 48px",
        }}
      >
        {/* Page Header */}
        <div className="flex flex-col" style={{ gap: 10 }}>
          <span
            className="text-xs font-semibold uppercase"
            style={{ color: "var(--color-ink-48)", letterSpacing: "0.04em" }}
          >
            {eyebrow}
          </span>
          <h1
            className="font-semibold"
            style={{ fontSize: 40, color: "var(--color-ink)", letterSpacing: "-0.02em" }}
          >
            {heading}
          </h1>
          <p className="text-[17px]" style={{ color: "var(--color-ink-48)" }}>
            {subtitle}
          </p>
          {/* 视角切换器：切换后雷达 / 匹配度 / 缺口全部跟随 */}
          <div style={{ paddingTop: 2 }}>
            <RoleSwitcher options={roleOptions} active={viewRole} />
          </div>
        </div>

        {/* KPI Cards Row */}
        <KpiCards
          career={career}
          tasks={tasks}
          tasksTotal={tasksTotal}
          agentRuns={agentRuns}
          readiness={readiness}
          readinessLabel={isEmbodied ? "具身能力就绪度" : "岗位匹配度"}
          readinessSub={
            activeTrack
              ? `按「${activeTrack.name}」的 ${activeTrack.skillCount} 项硬性要求技能计算`
              : "按当前视角赛道硬性要求技能计算"
          }
        />

        {/* Main Grid Row 1: Radar + Quick Actions */}
        <div className="flex" style={{ gap: "var(--spacing-lg)" }}>
          <SkillRadarCard
            axes={radarAxes}
            trackName={activeTrack?.name ?? null}
            readiness={readiness}
          />
          <div className="flex flex-1 flex-col" style={{ gap: "var(--spacing-lg)" }}>
            {/* Planner 输入应是全部技能，而非雷达轴子集 */}
            <QuickActions skills={skills} activeTrack={activeTrack} />
          </div>
        </div>

        {/* Main Grid Row 2: Tasks + Projects */}
        <div className="flex" style={{ gap: "var(--spacing-lg)" }}>
          <TodayTasks
            tasks={tasks}
            trackName={activeTrack?.name ?? null}
            totalCount={tasksTotal}
          />
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
