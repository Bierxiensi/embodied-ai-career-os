import type { RadarAxis } from "@/types";
import RadarChart from "./RadarChart";

type Props = {
  /** 雷达轴：主攻赛道的硬性要求技能（6–8 条）。 */
  axes: RadarAxis[];
  /** 主攻赛道名（来自后端配置，前端不硬编码）。 */
  trackName: string | null;
  /** 达成度 0-100，与 /jobs 页同源（主攻赛道 matchPct）。 */
  readiness: number;
};

/** 岗位对齐雷达卡片 — 雷达图 + 达成度面板，匹配设计稿布局。
 *
 * 轴的定义是**该主攻岗位的 required_skills**，而不是全量技能。
 * 早期实现用"全量技能 − 2 项排除"，会得到 46 条轴、34 个凸点，标签互相压叠且混入
 * 已冻结的具身技能 —— 形状没有解释力。改成岗位对齐后，这张图的含义变成
 * "离目标岗位的技能形状还差多少"，这才是求职期该看的图。
 *
 * 响应式：md+ 展示雷达图；窄屏降级为"达成度 + 技能缺口水平条形"，避免 360px 雷达溢出。
 * 轴标签由 RadarChart 内部绘制（本组件不再叠加一层绝对定位标签，避免双环标签）。
 */
export default function SkillRadarCard({ axes, trackName, readiness }: Props) {
  // 转换为 RadarChart 格式：target 取"岗位要求等级"而非技能自身 target_level，
  // 这样图上的目标轮廓 = 岗位硬性要求，与 readiness 口径一致。
  const radarSkills = axes.map((a) => ({
    name: a.name,
    current: a.current,
    target: a.required,
  }));

  // 缺口（仅未达标的轴，按差距降序）
  const gaps = axes
    .filter((a) => a.gap > 0)
    .map((a) => ({ name: a.name, gap: a.gap, current: a.current, target: a.required }))
    .sort((a, b) => b.gap - a.gap);

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
      <div className="flex flex-col" style={{ gap: 4 }}>
        <div className="flex items-center justify-between">
          <span className="text-[17px] font-semibold" style={{ color: "var(--color-ink)" }}>
            岗位对齐雷达
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
        <span className="text-xs" style={{ color: "var(--color-ink-48)" }}>
          轴 = {trackName ?? "主攻岗位"} 的 {axes.length} 项硬性要求技能
        </span>
      </div>

      {axes.length === 0 ? (
        <span className="text-[13px]" style={{ color: "var(--color-ink-48)", paddingBlock: 24 }}>
          暂无赛道数据（后端 target_roles 为空，或 /api/job-hunt 暂不可用）
        </span>
      ) : (
        <>
          {/* ===== 桌面 / 平板：雷达图 + 达成度面板 ===== */}
          <div className="hidden md:flex flex-wrap" style={{ gap: 28 }}>
            <div className="flex-shrink-0" style={{ width: 360 }}>
              <RadarChart skills={radarSkills} size={360} />
            </div>

            {/* Readiness panel */}
            <div className="flex flex-1 flex-col" style={{ gap: 14, paddingTop: 88, minWidth: 180 }}>
              <span
                className="text-[11px] font-semibold uppercase"
                style={{ color: "var(--color-ink-48)", letterSpacing: "0.04em" }}
              >
                岗位要求达成度
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
              {gaps.length === 0 ? (
                <span className="text-xs" style={{ color: "var(--color-ink-48)" }}>
                  已满足该岗位全部硬性要求
                </span>
              ) : (
                gaps.slice(0, 3).map((gap) => {
                  const fillPct = (gap.current / gap.target) * 100;
                  const isCritical = gap.gap >= 2;
                  return (
                    <div key={gap.name} className="flex items-center" style={{ gap: 10 }}>
                      <span
                        className="whitespace-nowrap text-[13px] font-medium"
                        style={{ color: "var(--color-ink)" }}
                      >
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
                })
              )}
            </div>
          </div>

          {/* ===== 移动端：达成度 + 技能缺口水平条形（避免 360px 雷达溢出） ===== */}
          <div className="flex md:hidden flex-col" style={{ gap: 14 }}>
            <div className="flex items-baseline" style={{ gap: 10 }}>
              <span
                className="font-semibold"
                style={{ fontSize: 30, color: "var(--color-ink)", letterSpacing: "-0.01em" }}
              >
                {readiness}%
              </span>
              <span className="text-xs" style={{ color: "var(--color-ink-48)" }}>
                岗位要求达成度
              </span>
            </div>
            <span className="text-[13px] font-semibold" style={{ color: "var(--color-ink-80)" }}>
              技能缺口（按差距排序）
            </span>
            {gaps.length === 0 ? (
              <span className="text-xs" style={{ color: "var(--color-ink-48)" }}>
                已满足该岗位全部硬性要求
              </span>
            ) : (
              gaps.map((gap) => {
                const fillPct = (gap.current / gap.target) * 100;
                const isCritical = gap.gap >= 2;
                return (
                  <div key={gap.name} className="flex items-center" style={{ gap: 10 }}>
                    <span
                      className="whitespace-nowrap text-[13px] font-medium"
                      style={{ color: "var(--color-ink)", width: 92 }}
                    >
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
                    <span
                      className="whitespace-nowrap text-xs"
                      style={{ color: "var(--color-ink-48)", width: 36, textAlign: "right" }}
                    >
                      {gap.current}/{gap.target}
                    </span>
                  </div>
                );
              })
            )}
          </div>
        </>
      )}
    </div>
  );
}
