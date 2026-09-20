import type { AgentRunRecord, JobAppStatus, Task } from "@/types";

type Props = {
  /** 当前阶段范围内的任务。 */
  tasks: Task[];
  /** 被排除的冻结赛道任务数。 */
  excludedFrozen?: number;
  /** 范围内未归类任务数。 */
  unclassified?: number;
  agentRuns: AgentRunRecord[];
  /** 就绪度 0-100（当前赛道匹配度）。 */
  readiness?: number;
  /** 就绪度卡片标题（随赛道变化）。 */
  readinessLabel?: string;
  /** 就绪度卡片副标题。 */
  readinessSub?: string;
  /** 投递漏斗各阶段数量。 */
  applicationCounts?: Record<JobAppStatus, number>;
};

const FUNNEL_STAGES: { key: JobAppStatus; label: string; color: string }[] = [
  { key: "applied", label: "已投", color: "var(--color-ink-48)" },
  { key: "screening", label: "筛选", color: "var(--color-sky)" },
  { key: "interview", label: "面试", color: "var(--color-violet)" },
  { key: "offer", label: "Offer", color: "var(--color-emerald)" },
];

/** KPI 指标卡片行 — 4 个核心指标：
 *  就绪度 → 任务进度 → 投递漏斗 → Agent 运行
 */
export default function KpiCards({
  tasks,
  excludedFrozen = 0,
  unclassified = 0,
  agentRuns,
  readiness = 0,
  readinessLabel = "岗位匹配度",
  readinessSub = "按当前赛道硬性要求技能计算",
  applicationCounts,
}: Props) {
  const doneCount = tasks.filter((t) => t.status === "done").length;
  const totalCount = tasks.length;

  const successRuns = agentRuns.filter((r) => r.status === "success").length;
  const successRate = agentRuns.length > 0 ? Math.round((successRuns / agentRuns.length) * 100) : 0;

  const scopeNotes: string[] = [];
  if (excludedFrozen > 0) scopeNotes.push(`${excludedFrozen} 项冻结赛道已排除`);
  if (unclassified > 0) scopeNotes.push(`${unclassified} 项未归类`);
  const taskProgressSub =
    `共 ${totalCount} 项 · 完成 ${doneCount} 项` +
    (scopeNotes.length > 0 ? ` · ${scopeNotes.join(" · ")}` : "");

  // 投递漏斗
  const funnelTotal = applicationCounts
    ? Object.values(applicationCounts).reduce((a, b) => a + b, 0)
    : 0;

  const kpis = [
    {
      label: readinessLabel,
      value: `${readiness}%`,
      fillPct: readiness,
      fillColor: "var(--color-primary)",
      sub: readinessSub,
      subColor: "var(--color-primary)",
      icon: (
        <svg viewBox="0 0 30 30" fill="none" xmlns="http://www.w3.org/2000/svg">
          <path d="M4.5 21A11 11 0 0 1 25.5 21" stroke="var(--color-primary)" strokeWidth="1.5" fill="none" strokeLinecap="round" />
          <path d="M18 17L21 20" stroke="var(--color-primary)" strokeWidth="1.5" strokeLinecap="round" />
          <circle cx="15" cy="20" r="2" fill="var(--color-primary)" />
        </svg>
      ),
    },
    {
      label: "任务进度",
      value: `${doneCount}/${totalCount}`,
      fillPct: totalCount > 0 ? (doneCount / totalCount) * 100 : 0,
      fillColor: "var(--color-amber)",
      sub: taskProgressSub,
      subColor: "var(--color-amber-deep)",
      icon: (
        <svg viewBox="0 0 30 30" fill="none" xmlns="http://www.w3.org/2000/svg">
          <rect x="6" y="6" width="18" height="18" rx="3" stroke="var(--color-amber)" strokeWidth="1.5" fill="none" />
          <path d="M11 15L14 18L20 12" stroke="var(--color-amber)" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
        </svg>
      ),
    },
    {
      label: "投递漏斗",
      value: `${funnelTotal}`,
      fillPct: 0, // 漏斗不用进度条
      fillColor: "transparent",
      sub: applicationCounts
        ? FUNNEL_STAGES.map((s) => `${s.label} ${applicationCounts[s.key] ?? 0}`).join(" · ")
        : "暂无投递数据",
      subColor: "var(--color-ink-80)",
      icon: (
        <svg viewBox="0 0 30 30" fill="none" xmlns="http://www.w3.org/2000/svg">
          <path d="M5 8H25L20 15H10L5 8Z" stroke="var(--color-violet)" strokeWidth="1.5" fill="none" />
          <path d="M10 15H20L17 22H13L10 15Z" stroke="var(--color-violet)" strokeWidth="1.5" fill="none" />
        </svg>
      ),
    },
    {
      label: "Agent 运行",
      value: `${agentRuns.length}`,
      fillPct: successRate,
      fillColor: "var(--color-emerald)",
      sub:
        agentRuns.length > 0
          ? `最近 ${agentRuns.length} 次 · 成功率 ${successRate}%`
          : "暂无运行记录",
      subColor: "var(--color-emerald-deep)",
      icon: (
        <svg viewBox="0 0 30 30" fill="none" xmlns="http://www.w3.org/2000/svg">
          <rect x="7" y="10" width="16" height="12" rx="2" stroke="var(--color-emerald)" strokeWidth="1.5" fill="none" />
          <circle cx="12" cy="16" r="1.5" fill="var(--color-emerald)" />
          <circle cx="18" cy="16" r="1.5" fill="var(--color-emerald)" />
          <path d="M12 7L15 10L18 7" stroke="var(--color-emerald)" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
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
                background: "var(--color-primary-soft)",
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
          {kpi.fillPct > 0 && (
            <div
              className="w-full overflow-hidden"
              style={{
                height: 5,
                background: "var(--color-zinc-100)",
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
          )}
          <span
            className="text-xs"
            style={{ color: kpi.subColor, fontWeight: 500 }}
          >
            {kpi.sub}
          </span>
        </div>
      ))}
    </div>
  );
}
