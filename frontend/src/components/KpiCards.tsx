import type { AgentRunRecord, Career, Task } from "@/types";

type Props = {
  career: Career | null;
  tasks: Task[];
  agentRuns: AgentRunRecord[];
  readiness?: number; // 0-100, from SkillGapSummary
};

/** KPI 指标卡片行 — 4 个核心指标。 */
export default function KpiCards({ career, tasks, agentRuns, readiness = 0 }: Props) {
  const progress = career?.progress ?? 0;
  const targetRole = career?.targetRole ?? "未设定";

  const doneCount = tasks.filter((t) => t.status === "done").length;
  const totalCount = tasks.length;

  const successRuns = agentRuns.filter((r) => r.status === "success").length;
  const successRate = agentRuns.length > 0 ? Math.round((successRuns / agentRuns.length) * 100) : 0;

  const kpis = [
    {
      label: "职业目标进度",
      value: `${progress}%`,
      fillPct: progress,
      fillColor: "var(--color-emerald)",
      sub: `按里程碑 · 目标 ${targetRole} · 2027`,
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
      label: "AI 能力就绪度",
      value: `${readiness}%`,
      fillPct: readiness,
      fillColor: "var(--color-primary)",
      sub: "按能力评分 · 较上周 +4%",
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
      label: "今日任务",
      value: `${doneCount}/${totalCount}`,
      fillPct: totalCount > 0 ? (doneCount / totalCount) * 100 : 0,
      fillColor: "var(--color-amber)",
      sub: `${totalCount - doneCount} 项待完成`,
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
      label: "Agent 执行",
      value: `${agentRuns.length}`,
      fillPct: successRate,
      fillColor: "var(--color-emerald)",
      sub: `成功率 ${successRate}% · 本周`,
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
