import type { RiskOut, RiskDimension } from "@/types";

type RiskLevel = RiskDimension["level"];

/** 维度等级 → 雷达半径比例（red 最外 = 风险最大，green 最内 = 风险最小）。 */
const LEVEL_RATIO: Record<RiskLevel, number> = {
  red: 1.0,
  amber: 0.66,
  green: 0.34,
};

/** 维度等级 → 语义色（禁止硬编码 hex）。 */
const LEVEL_COLOR: Record<RiskLevel, string> = {
  red: "var(--accent-danger)",
  amber: "var(--accent-warning)",
  green: "var(--accent-success)",
};

const LEVEL_LABEL: Record<RiskLevel, string> = {
  red: "高风险",
  amber: "中风险",
  green: "低风险",
};

/** 极坐标转笛卡尔坐标：0° 朝上（北方），顺时针递增。 */
function polarToCartesian(
  cx: number,
  cy: number,
  radius: number,
  angleDeg: number
): { x: number; y: number } {
  const rad = ((angleDeg - 90) * Math.PI) / 180;
  return {
    x: cx + radius * Math.cos(rad),
    y: cy + radius * Math.sin(rad),
  };
}

type Props = {
  /** 七维风险（后端已按固定参考日计算）。 */
  risk: RiskOut;
  /** SVG 画布尺寸，默认 360。 */
  size?: number;
};

/** Phase 2 风险雷达卡片 — 纯 SVG 七轴雷达 + 逐维原因。
 *
 * 设计要点（对齐 §一 规格 D）：
 *  - 轴色按 level：red=var(--accent-danger) / amber=var(--accent-warning) / green=var(--accent-success)
 *  - 白底卡片 + hairline 边框 + 18px 圆角（var(--radius-lg)），全程禁硬编码 hex
 *  - 雷达下方逐维一行 reason 文本，便于直接读"为什么是该等级"
 *
 * 半径语义：red 顶点最外（风险敞口最大），green 最内（安全），符合风险雷达直觉。
 */
export default function RiskRadar({ risk, size = 360 }: Props) {
  const dims = risk.dimensions;
  const count = dims.length;

  const cx = size / 2;
  const cy = size / 2;
  const radius = size / 2 - 64; // 留边距给轴标签

  // 参考同心环（3 层，对应 red / amber / green 比例），用 hairline 描边
  const rings = [LEVEL_RATIO.red, LEVEL_RATIO.amber, LEVEL_RATIO.green].map(
    (ratio) =>
      dims
        .map((_, i) => {
          const angle = (360 / count) * i;
          const { x, y } = polarToCartesian(cx, cy, radius * ratio, angle);
          return `${x.toFixed(2)},${y.toFixed(2)}`;
        })
        .join(" ")
  );

  // 各轴端点（满半径）与顶点（按 level 比例）
  const axisEnds = dims.map((_, i) =>
    polarToCartesian(cx, cy, radius, (360 / count) * i)
  );
  const points = dims.map((d, i) => {
    const angle = (360 / count) * i;
    const r = radius * LEVEL_RATIO[d.level];
    return polarToCartesian(cx, cy, r, angle);
  });

  const polygon = points.map((p) => `${p.x.toFixed(2)},${p.y.toFixed(2)}`).join(" ");
  const overallColor = LEVEL_COLOR[risk.overallLevel];

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
      <div className="flex items-center justify-between">
        <span className="text-[17px] font-semibold" style={{ color: "var(--text-primary)" }}>
          职业风险雷达
        </span>
        <div className="flex items-center" style={{ gap: 8 }}>
          <span
            className="text-xs font-semibold"
            style={{
              color: overallColor,
              padding: "2px 10px",
              borderRadius: "var(--radius-pill)",
              border: `1px solid ${overallColor}`,
            }}
          >
            综合 {LEVEL_LABEL[risk.overallLevel]}
          </span>
        </div>
      </div>

      {/* 雷达图（窄屏也保留：7 轴标签精简，不会溢出） */}
      <div className="flex justify-center" style={{ width: "100%" }}>
        <svg
          viewBox={`0 0 ${size} ${size}`}
          className="h-auto w-full"
          style={{ maxWidth: size }}
          role="img"
          aria-label="职业风险七维雷达图"
        >
          {/* 参考同心环 */}
          {rings.map((pts, i) => (
            <polygon
              key={i}
              points={pts}
              fill="none"
              stroke="var(--border-default)"
              strokeWidth={1}
            />
          ))}

          {/* 坐标轴：按该维 level 着色 */}
          {axisEnds.map((end, i) => (
            <line
              key={i}
              x1={cx}
              y1={cy}
              x2={end.x}
              y2={end.y}
              stroke={LEVEL_COLOR[dims[i].level]}
              strokeWidth={1}
              strokeOpacity={0.55}
            />
          ))}

          {/* 风险多边形（按综合等级着色，半透明填充） */}
          <polygon
            points={polygon}
            fill={overallColor}
            fillOpacity={0.14}
            stroke={overallColor}
            strokeWidth={2}
            strokeLinejoin="round"
          />

          {/* 顶点圆点 + 轴标签 */}
          {dims.map((d, i) => {
            const angle = (360 / count) * i;
            const labelPos = polarToCartesian(cx, cy, radius + 22, angle);
            const isLeft = labelPos.x < cx - 4;
            const isRight = labelPos.x > cx + 4;
            const anchor = isLeft ? "end" : isRight ? "start" : "middle";
            return (
              <g key={d.key}>
                <circle cx={points[i].x} cy={points[i].y} r={4} fill={LEVEL_COLOR[d.level]} />
                <text
                  x={labelPos.x}
                  y={labelPos.y}
                  textAnchor={anchor}
                  dominantBaseline="middle"
                  style={{ fontSize: 11, fontWeight: 600, fill: "var(--text-secondary)" }}
                >
                  {d.label}
                </text>
              </g>
            );
          })}
        </svg>
      </div>

      {/* 逐维原因：每行 等级徽标 + 原因文本 */}
      <div className="flex flex-col" style={{ gap: 8 }}>
        {dims.map((d) => (
          <div
            key={d.key}
            className="flex items-start"
            style={{ gap: 10, paddingTop: 8, borderTop: "1px solid var(--border-default)" }}
          >
            <span
              className="text-[11px] font-semibold shrink-0"
              style={{
                color: LEVEL_COLOR[d.level],
                background: "var(--surface-canvas)",
                border: `1px solid ${LEVEL_COLOR[d.level]}`,
                borderRadius: "var(--radius-pill)",
                padding: "1px 8px",
                marginTop: 1,
              }}
            >
              {LEVEL_LABEL[d.level]}
            </span>
            <span className="text-[13px]" style={{ color: "var(--text-secondary)", lineHeight: 1.6 }}>
              <span style={{ fontWeight: 600, color: "var(--text-primary)" }}>{d.label}：</span>
              {d.reason}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}
