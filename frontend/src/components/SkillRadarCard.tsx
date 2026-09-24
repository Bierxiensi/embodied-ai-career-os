import type { RadarGapRow, SkillRadarData } from "@/types";
import RadarChart from "./RadarChart";

type Props = {
  /** 已适配好的雷达数据（模式 → variant 的取舍在 services/skillRadarService）。 */
  data: SkillRadarData;
};

/** 缺口条形图的一行（桌面 Top3 与移动端全量共用，避免两处样式漂移）。 */
function GapBar({
  gap,
  labelWidth,
}: {
  gap: RadarGapRow;
  labelWidth?: number;
}) {
  // current/target 都是同一量纲 0-5；target 为 0 时按满格处理，避免除零
  const fillPct = gap.target > 0 ? (gap.current / gap.target) * 100 : 0;
  const isCritical = gap.gap >= 2;

  return (
    <div className="flex flex-col" style={{ gap: 4 }}>
      <div className="flex items-center" style={{ gap: 10 }}>
        <span
          className="whitespace-nowrap text-[13px] font-medium"
          style={{
            color: "var(--text-primary)",
            ...(labelWidth ? { width: labelWidth } : null),
          }}
        >
          {gap.name}
        </span>
        <div
          className="flex-1 overflow-hidden"
          style={{
            height: labelWidth ? 6 : 5,
            background: "var(--color-zinc-100)",
            borderRadius: "var(--radius-pill)",
          }}
        >
          <div
            className="h-full"
            style={{
              width: `${fillPct}%`,
              background: isCritical ? "var(--accent-danger)" : "var(--accent-warning)",
              borderRadius: "var(--radius-pill)",
            }}
          />
        </div>
        <span
          className="whitespace-nowrap text-xs"
          style={{
            color: "var(--text-muted)",
            ...(labelWidth ? { width: 46, textAlign: "right" as const } : null),
          }}
        >
          {gap.ratioLabel}
        </span>
      </div>
      {gap.hint ? (
        <span
          className="text-[11px]"
          style={{
            color: "var(--text-muted)",
            paddingLeft: labelWidth ?? 0,
            lineHeight: 1.5,
          }}
        >
          {gap.hint}
        </span>
      ) : null}
    </div>
  );
}

/** 移动端缺口条形的显示上限。
 *
 * R2 域视图的缺口行可达 30+ 条（六域里所有未达标技能），全量铺在手机上
 * 会把卡片拉成一屏半的条形图。限前 8 条 + 明示总数，剩下的去明细页看。
 */
const MOBILE_GAP_LIMIT = 8;

/** 技能雷达卡片 — 雷达图 + 达成度面板 + 缺口条形。
 *
 * 两种形态（由 `data.variant` 决定，组件不判断当前模式）：
 *  - `job`    R1 岗位对齐：轴 = 主攻岗位的硬性要求技能（求职期）
 *  - `domain` R2 域聚合：轴 = 能力六域（在职转型期）
 *
 * 历史注记：早期实现用"全量技能 − 2 项排除"，会得到 46 条轴、34 个凸点，
 * 标签互相压叠且混入已冻结的具身技能 —— 形状没有解释力。R1 改成岗位对齐后，
 * 这张图的含义变成"离目标岗位的技能形状还差多少"；R2 进一步把轴降到六域，
 * 让转型期看到的是"哪个能力域整体薄"，而不是逐项技能的 1 级差。
 *
 * 响应式：md+ 展示雷达图 + 面板；窄屏降级为"达成度 + 缺口水平条形"，
 * 避免 360px 雷达在手机上溢出。轴标签由 RadarChart 内部绘制。
 */
export default function SkillRadarCard({ data }: Props) {
  const { axes, gaps, readiness } = data;
  const hasAxes = axes.length > 0;

  return (
    <div
      className="flex flex-col"
      style={{
        flex: "1 1 420px",
        maxWidth: 690,
        minWidth: 0,
        gap: "var(--spacing-md)",
        padding: "var(--spacing-lg)",
        background: "var(--surface-card)",
        border: "1px solid var(--border-default)",
        borderRadius: "var(--radius-lg)",
      }}
    >
      {/* Card header */}
      <div className="flex flex-col" style={{ gap: 4 }}>
        <div className="flex items-center justify-between">
          <span className="text-[17px] font-semibold" style={{ color: "var(--text-primary)" }}>
            {data.title}
          </span>
          <div className="hidden md:flex items-center" style={{ gap: 14 }}>
            <div className="flex items-center" style={{ gap: 6 }}>
              <span
                style={{
                  width: 8,
                  height: 8,
                  borderRadius: "var(--radius-pill)",
                  background: "var(--accent-success)",
                  display: "inline-block",
                }}
              />
              <span className="text-xs" style={{ color: "var(--text-muted)" }}>
                当前
              </span>
            </div>
            <div className="flex items-center" style={{ gap: 6 }}>
              <span
                style={{
                  width: 8,
                  height: 8,
                  borderRadius: "var(--radius-pill)",
                  background: "var(--accent-primary)",
                  display: "inline-block",
                }}
              />
              <span className="text-xs" style={{ color: "var(--text-muted)" }}>
                目标
              </span>
            </div>
          </div>
        </div>
        <span className="text-xs" style={{ color: "var(--text-muted)" }}>
          {data.axisCaption}
        </span>
      </div>

      {!hasAxes ? (
        <span className="text-[13px]" style={{ color: "var(--text-muted)", paddingBlock: 24 }}>
          {data.emptyHint}
        </span>
      ) : (
        <>
          {/* ===== 桌面 / 平板：雷达图 + 达成度面板 ===== */}
          <div className="hidden md:flex flex-wrap" style={{ gap: 28 }}>
            <div className="flex-shrink-0" style={{ width: 360 }}>
              <RadarChart
                skills={axes.map((a) => ({
                  name: a.name,
                  current: a.current,
                  target: a.required,
                }))}
                size={360}
              />
            </div>

            {/* Readiness panel */}
            <div className="flex flex-1 flex-col" style={{ gap: 14, paddingTop: 88, minWidth: 180 }}>
              <span
                className="text-[11px] font-semibold uppercase"
                style={{ color: "var(--text-muted)", letterSpacing: "0.04em" }}
              >
                {data.readinessCaption}
              </span>
              <span
                className="font-semibold"
                style={{ fontSize: 30, color: "var(--text-primary)", letterSpacing: "-0.01em" }}
              >
                {readiness}%
              </span>
              {data.readinessNote ? (
                <span className="text-xs" style={{ color: "var(--text-muted)", lineHeight: 1.6 }}>
                  {data.readinessNote}
                </span>
              ) : null}
              <div className="flex items-baseline justify-between" style={{ gap: 8, marginTop: 4 }}>
                <span className="text-[13px] font-semibold" style={{ color: "var(--text-secondary)" }}>
                  最大缺口 Top 3
                </span>
                {gaps.length > 0 ? (
                  <span className="text-[11px]" style={{ color: "var(--text-muted)" }}>
                    共 {gaps.length} 项待补
                  </span>
                ) : null}
              </div>
              {gaps.length === 0 ? (
                <span className="text-xs" style={{ color: "var(--text-muted)" }}>
                  已满足全部要求
                </span>
              ) : (
                <div className="flex flex-col" style={{ gap: 10 }}>
                  {gaps.slice(0, 3).map((gap) => (
                    <GapBar key={gap.name} gap={gap} />
                  ))}
                </div>
              )}
            </div>
          </div>

          {/* ===== 移动端：达成度 + 缺口水平条形（避免 360px 雷达溢出） ===== */}
          <div className="flex md:hidden flex-col" style={{ gap: 14 }}>
            <div className="flex items-baseline" style={{ gap: 10 }}>
              <span
                className="font-semibold"
                style={{ fontSize: 30, color: "var(--text-primary)", letterSpacing: "-0.01em" }}
              >
                {readiness}%
              </span>
              <span className="text-xs" style={{ color: "var(--text-muted)" }}>
                {data.readinessCaption}
              </span>
            </div>
            <span className="text-[13px] font-semibold" style={{ color: "var(--text-secondary)" }}>
              缺口（按差距排序）
            </span>
            {gaps.length === 0 ? (
              <span className="text-xs" style={{ color: "var(--text-muted)" }}>
                已满足全部要求
              </span>
            ) : (
              <div className="flex flex-col" style={{ gap: 10 }}>
                {gaps.slice(0, MOBILE_GAP_LIMIT).map((gap) => (
                  <GapBar key={gap.name} gap={gap} labelWidth={92} />
                ))}
                {gaps.length > MOBILE_GAP_LIMIT ? (
                  <span className="text-[11px]" style={{ color: "var(--text-muted)" }}>
                    另有 {gaps.length - MOBILE_GAP_LIMIT} 项待补未显示
                  </span>
                ) : null}
              </div>
            )}
          </div>
        </>
      )}
    </div>
  );
}
