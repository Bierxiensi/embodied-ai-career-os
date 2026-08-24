import type { Skill } from "@/types";
import RadarChart from "./RadarChart";

type Props = {
  skills: Skill[];
};

/** 能力雷达卡片 — 雷达图 + 就绪度面板，匹配设计稿布局。
 *  响应式：md+ 展示雷达图；窄屏（手机）降级为"就绪度 + 能力缺口水平条形"，避免 360px 雷达溢出。 */
export default function SkillRadarCard({ skills }: Props) {
  // 计算就绪度
  const totalCurrent = skills.reduce((s, sk) => s + sk.level, 0);
  const totalTarget = skills.reduce((s, sk) => s + sk.targetLevel, 0);
  const readiness = totalTarget > 0 ? Math.round((totalCurrent / totalTarget) * 100) : 0;

  // 计算缺口（全部技能，按缺口降序）
  const gaps = skills
    .map((s) => ({ name: s.name, gap: s.targetLevel - s.level, current: s.level, target: s.targetLevel }))
    .filter((g) => g.gap > 0)
    .sort((a, b) => b.gap - a.gap);

  // 转换为 RadarChart 格式
  const radarSkills = skills.map((s) => ({
    name: s.name,
    current: s.level,
    target: s.targetLevel,
  }));

  return (
    <div
      className="flex flex-col"
      style={{
        flex: "1 1 420px",
        maxWidth: 690,
        minWidth: 0,
        gap: "var(--spacing-md)",
        padding: "var(--spacing-lg)",
        background: "var(--color-card)",
        border: "1px solid var(--color-hairline)",
        borderRadius: "var(--radius-card-lg)",
      }}
    >
      {/* Card header */}
      <div className="flex items-center justify-between">
        <span className="text-[17px] font-semibold" style={{ color: "var(--color-ink)" }}>
          能力雷达
        </span>
        <div className="hidden md:flex items-center" style={{ gap: 14 }}>
          <div className="flex items-center" style={{ gap: 6 }}>
            <span
              style={{
                width: 8,
                height: 8,
                borderRadius: "var(--radius-pill)",
                background: "var(--color-emerald)",
                display: "inline-block",
              }}
            />
            <span className="text-xs" style={{ color: "var(--color-ink-48)" }}>
              当前
            </span>
          </div>
          <div className="flex items-center" style={{ gap: 6 }}>
            <span
              style={{
                width: 8,
                height: 8,
                borderRadius: "var(--radius-pill)",
                background: "var(--color-primary)",
                display: "inline-block",
              }}
            />
            <span className="text-xs" style={{ color: "var(--color-ink-48)" }}>
              目标
            </span>
          </div>
        </div>
      </div>

      {/* ===== 桌面 / 平板：雷达图 + 就绪度面板 ===== */}
      <div className="hidden md:flex flex-wrap" style={{ gap: 28 }}>
        {/* Radar chart with axis labels */}
        <div className="relative flex-shrink-0" style={{ width: 360, height: 360 }}>
          <RadarChart skills={radarSkills} size={360} />
          {skills.map((skill, i) => {
            const angle = (360 / skills.length) * i;
            const rad = ((angle - 90) * Math.PI) / 180;
            const labelR = 190; // distance from center
            const x = 180 + labelR * Math.cos(rad);
            const y = 180 + labelR * Math.sin(rad);
            return (
              <span
                key={skill.name}
                className="absolute whitespace-nowrap text-[11px] font-medium"
                style={{
                  left: x,
                  top: y,
                  transform: "translate(-50%, -50%)",
                  color: "var(--color-ink-28)",
                }}
              >
                {skill.name}
              </span>
            );
          })}
        </div>

        {/* Readiness panel */}
        <div className="flex flex-1 flex-col" style={{ gap: 14, paddingTop: 88, minWidth: 180 }}>
          <span
            className="text-[11px] font-semibold uppercase"
            style={{ color: "var(--color-ink-48)", letterSpacing: "0.04em" }}
          >
            Robot AI Readiness
          </span>
          <span
            className="font-semibold"
            style={{ fontSize: 30, color: "var(--color-ink)", letterSpacing: "-0.01em" }}
          >
            {readiness}%
          </span>
          <span className="text-[13px] font-semibold" style={{ color: "var(--color-ink-80)", marginTop: 4 }}>
            最大缺口 Top 3
          </span>
          {gaps.slice(0, 3).map((gap) => {
            const fillPct = (gap.current / gap.target) * 100;
            const isCritical = gap.gap >= 3;
            return (
              <div key={gap.name} className="flex items-center" style={{ gap: 10 }}>
                <span className="whitespace-nowrap text-[13px] font-medium" style={{ color: "var(--color-ink)" }}>
                  {gap.name}
                </span>
                <div
                  className="flex-1 overflow-hidden"
                  style={{ height: 5, background: "#F4F4F5", borderRadius: "var(--radius-pill)" }}
                >
                  <div
                    className="h-full"
                    style={{
                      width: `${fillPct}%`,
                      background: isCritical ? "var(--color-rose)" : "var(--color-amber)",
                      borderRadius: "var(--radius-pill)",
                    }}
                  />
                </div>
                <span className="whitespace-nowrap text-xs" style={{ color: "var(--color-ink-48)" }}>
                  {gap.current}/{gap.target}
                </span>
              </div>
            );
          })}
        </div>
      </div>

      {/* ===== 移动端：就绪度 + 能力缺口水平条形（避免 360px 雷达溢出） ===== */}
      <div className="flex md:hidden flex-col" style={{ gap: 14 }}>
        <div className="flex items-baseline" style={{ gap: 10 }}>
          <span
            className="font-semibold"
            style={{ fontSize: 30, color: "var(--color-ink)", letterSpacing: "-0.01em" }}
          >
            {readiness}%
          </span>
          <span className="text-xs" style={{ color: "var(--color-ink-48)" }}>
            Robot AI 能力就绪度
          </span>
        </div>
        <span className="text-[13px] font-semibold" style={{ color: "var(--color-ink-80)" }}>
          能力缺口（按差距排序）
        </span>
        {gaps.length === 0 ? (
          <span className="text-xs" style={{ color: "var(--color-ink-48)" }}>
            暂无缺口，已达成全部目标等级 🎉
          </span>
        ) : (
          gaps.map((gap) => {
            const fillPct = (gap.current / gap.target) * 100;
            const isCritical = gap.gap >= 3;
            return (
              <div key={gap.name} className="flex items-center" style={{ gap: 10 }}>
                <span className="whitespace-nowrap text-[13px] font-medium" style={{ color: "var(--color-ink)", width: 64 }}>
                  {gap.name}
                </span>
                <div
                  className="flex-1 overflow-hidden"
                  style={{ height: 6, background: "#F4F4F5", borderRadius: "var(--radius-pill)" }}
                >
                  <div
                    className="h-full"
                    style={{
                      width: `${fillPct}%`,
                      background: isCritical ? "var(--color-rose)" : "var(--color-amber)",
                      borderRadius: "var(--radius-pill)",
                    }}
                  />
                </div>
                <span className="whitespace-nowrap text-xs" style={{ color: "var(--color-ink-48)", width: 36, textAlign: "right" }}>
                  {gap.current}/{gap.target}
                </span>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}
