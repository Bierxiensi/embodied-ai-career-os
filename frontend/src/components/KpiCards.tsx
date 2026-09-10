import type { AgentRunRecord, Career, Task } from "@/types";

type Props = {
  career: Career | null;
  /** **本视角**的任务（已按赛道过滤） */
  tasks: Task[];
  /** 全量任务数（跨赛道）；与 tasks.length 不同时副标题会点出全量口径 */
  tasksTotal?: number;
  agentRuns: AgentRunRecord[];
  /** 0-100，与 /jobs 页同源（当前视角赛道 matchPct）。 */
  readiness?: number;
  /** 就绪度卡片的标题文案（随视角变化，避免硬编码）。 */
  readinessLabel?: string;
  /** 就绪度卡片的副标题（说明数字口径，避免与「里程碑进度」混淆）。 */
  readinessSub?: string;
};

/** KPI 指标卡片行 — 4 个核心指标。
 *
 * 口径说明（审计修正，2026-09-10）：四个数字分别回答不同问题，副标题必须写明口径，
 * 否则会出现「35% 和 75% 到底看哪个」的困惑：
 *   - 里程碑进度  → 求职主线项目的里程碑完成度（过程指标）
 *   - 就绪度      → 当前视角赛道的硬性技能匹配度（能力指标，随视角切换）
 *   - 任务进度    → 任务池完成情况（执行指标）
 *   - Agent 运行  → 最近若干次 Agent 运行情况（系统指标）
 */
export default function KpiCards({
  career,
  tasks,
  tasksTotal,
  agentRuns,
  readiness = 0,
  readinessLabel = "AI 能力就绪度",
  readinessSub = "按当前视角赛道硬性要求技能计算",
}: Props) {
  const progress = career?.progress ?? 0;
  const targetRole = career?.targetRole ?? "未设定";
  const timeframe = career?.timeframe ?? "未设定";

  const doneCount = tasks.filter((t) => t.status === "done").length;
  const totalCount = tasks.length;

  const successRuns = agentRuns.filter((r) => r.status === "success").length;
  const successRate = agentRuns.length > 0 ? Math.round((successRuns / agentRuns.length) * 100) : 0;

  const kpis = [
    {
      label: "里程碑进度",
      value: `${progress}%`,
      fillPct: progress,
      fillColor: "var(--color-emerald)",
      // 原文案「职业目标进度 / 按里程碑」没说清是「哪个里程碑」，与右侧的技能匹配度
      // 并列时用户不知道看哪个。改为显式说明是求职主线项目的里程碑完成度。
      sub: `主线项目里程碑 · 目标 ${targetRole} · 截止 ${timeframe}`,
      subClass: "",
      iconBg: "var(--color-primary-soft)",
      icon: (
        <svg viewBox="0 0 30 30" fill="none" xmlns="http://www.w3.org/2000/svg">
          <circle cx="15" cy="15" r="11.25" stroke="#0066CC" strokeWidth="1.5" fill="none" />
          <circle cx="15" cy="15" r="5.625" stroke="#0066CC" strokeWidth="1.5" fill="none" />
          <circle cx="15" cy="15" r="1.625" fill="#0066CC" />
        </svg>
      ),
    },
    {
      label: readinessLabel,
      value: `${readiness}%`,
      fillPct: readiness,
      fillColor: "var(--color-primary)",
      sub: readinessSub,
      subClass: "emerald",
      iconBg: "var(--color-primary-soft)",
      icon: (
        <svg viewBox="0 0 30 30" fill="none" xmlns="http://www.w3.org/2000/svg">
          <path d="M4.5 21A11 11 0 0 1 25.5 21" stroke="#0066CC" strokeWidth="1.5" fill="none" strokeLinecap="round" />
          <path d="M18 17L21 20" stroke="#0066CC" strokeWidth="1.5" strokeLinecap="round" />
          <circle cx="15" cy="20" r="2" fill="#0066CC" />
        </svg>
      ),
    },
    {
      // 原名「今日任务」名不副实：这个数字来自任务池全量，并按 created_at 倒序取回，
      // 并没有「今日」这层过滤。改名 + 副标题说明口径（审计问题之一）。
      // 2026-09-10：tasks 现已按视角赛道过滤，副标题随之改为"本视角"口径。
      label: "任务进度",
      value: `${doneCount}/${totalCount}`,
      fillPct: totalCount > 0 ? (doneCount / totalCount) * 100 : 0,
      fillColor: "var(--color-amber)",
      sub:
        tasksTotal !== undefined && tasksTotal !== totalCount
          ? `本视角 ${totalCount} 项 · 完成 ${doneCount} 项 · 全量 ${tasksTotal} 项`
          : `任务池共 ${totalCount} 项 · 待完成 ${totalCount - doneCount} 项`,
      subClass: "amber",
      iconBg: "var(--color-amber-soft)",
      icon: (
        <svg viewBox="0 0 30 30" fill="none" xmlns="http://www.w3.org/2000/svg">
          <rect x="6" y="6" width="18" height="18" rx="3" stroke="#F59E0B" strokeWidth="1.5" fill="none" />
          <path d="M11 15L14 18L20 12" stroke="#F59E0B" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
        </svg>
      ),
    },
    {
      // 原副标题「成功率 100% · 本周」是错的：agentRuns 只取最近 10 条，
      // 并没有按「本周」过滤。改为如实描述样本范围（审计问题之一）。
      label: "Agent 运行",
      value: `${agentRuns.length}`,
      fillPct: successRate,
      fillColor: "var(--color-emerald)",
      sub:
        agentRuns.length > 0
          ? `最近 ${agentRuns.length} 次 · 成功率 ${successRate}%`
          : "暂无运行记录",
      subClass: "emerald",
      iconBg: "var(--color-emerald-soft)",
      icon: (
        <svg viewBox="0 0 30 30" fill="none" xmlns="http://www.w3.org/2000/svg">
          <rect x="7" y="10" width="16" height="12" rx="2" stroke="#10B981" strokeWidth="1.5" fill="none" />
          <circle cx="12" cy="16" r="1.5" fill="#10B981" />
          <circle cx="18" cy="16" r="1.5" fill="#10B981" />
          <path d="M12 7L15 10L18 7" stroke="#10B981" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
        </svg>
      ),
    },
  ];

  return (
    <div className="flex" style={{ gap: "var(--spacing-md)" }}>
      {kpis.map((kpi) => (
        <div
          key={kpi.label}
          className="flex flex-1 flex-col"
          style={{
            gap: "var(--spacing-sm)",
            padding: 22,
            background: "var(--color-card)",
            border: "1px solid var(--color-hairline)",
            borderRadius: "var(--radius-card-lg)",
          }}
        >
          <div className="flex items-center" style={{ gap: 10 }}>
            <div
              className="flex items-center justify-center"
              style={{
                width: 30,
                height: 30,
                borderRadius: "var(--radius-item-sm)",
                background: kpi.iconBg,
              }}
            >
              {kpi.icon}
            </div>
            <span className="text-sm" style={{ color: "var(--color-ink-48)" }}>
              {kpi.label}
            </span>
          </div>
          <span
            className="font-semibold"
            style={{ fontSize: 34, color: "var(--color-ink)", letterSpacing: "-0.01em" }}
          >
            {kpi.value}
          </span>
          <div
            className="w-full overflow-hidden"
            style={{
              height: 5,
              background: "#F4F4F5",
              borderRadius: "var(--radius-pill)",
            }}
          >
            <div
              className="h-full"
              style={{
                width: `${kpi.fillPct}%`,
                background: kpi.fillColor,
                borderRadius: "var(--radius-pill)",
              }}
            />
          </div>
          <span
            className="text-xs"
            style={{
              color: kpi.subClass === "emerald" ? "var(--color-emerald-deep)" : kpi.subClass === "amber" ? "var(--color-amber-deep)" : "var(--color-ink-48)",
              fontWeight: kpi.subClass ? 500 : 400,
            }}
          >
            {kpi.sub}
          </span>
        </div>
      ))}
    </div>
  );
}
