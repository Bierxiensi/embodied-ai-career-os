"use client";

import { useMemo, useState } from "react";

/** 雷达图技能数据项（RadarChart 与 SkillOverview 的契约）。 */
export interface RadarSkill {
  name: string;
  current: number; // 当前等级 0-5
  target: number; // 目标等级 0-5
}

type Props = {
  skills: RadarSkill[];
  size?: number; // SVG 画布尺寸，默认 360
  maxLevel?: number; // 最大等级，默认 5
};

/** 极坐标转笛卡尔坐标。
 * 角度约定：0° 朝上（北方），顺时针递增，符合雷达图直觉。
 * 抽出为纯函数便于测试与复用。
 */
function polarToCartesian(
  cx: number,
  cy: number,
  radius: number,
  angleDeg: number
): { x: number; y: number } {
  // -90° 让 0° 朝上；顺时针方向
  const rad = ((angleDeg - 90) * Math.PI) / 180;
  return {
    x: cx + radius * Math.cos(rad),
    y: cy + radius * Math.sin(rad),
  };
}

/** 生成多边形顶点字符串（SVG points 属性）。
 * 给定技能数与等级，计算每个顶点坐标并拼成 "x1,y1 x2,y2 ..."。
 */
function buildPolygonPoints(
  cx: number,
  cy: number,
  radius: number,
  count: number,
  values: number[],
  maxLevel: number
): string {
  return values
    .map((value, i) => {
      const angle = (360 / count) * i;
      const r = (Math.min(value, maxLevel) / maxLevel) * radius;
      const { x, y } = polarToCartesian(cx, cy, r, angle);
      return `${x.toFixed(2)},${y.toFixed(2)}`;
    })
    .join(" ");
}

export default function RadarChart({
  skills,
  size = 360,
  maxLevel = 5,
}: Props) {
  const [hoverIndex, setHoverIndex] = useState<number | null>(null);

  const cx = size / 2;
  const cy = size / 2;
  const radius = size / 2 - 56; // 留边距给标签
  const count = skills.length;

  // 预计算各层背景多边形（1..maxLevel）与坐标轴端点
  const { gridLayers, axisEnds, currentPoints, targetPoints } = useMemo(() => {
    const layers = Array.from({ length: maxLevel }, (_, i) => i + 1).map(
      (lvl) =>
        buildPolygonPoints(
          cx,
          cy,
          radius,
          count,
          Array(count).fill(lvl),
          maxLevel
        )
    );
    const ends = skills.map((_, i) => {
      const angle = (360 / count) * i;
      return polarToCartesian(cx, cy, radius, angle);
    });
    return {
      gridLayers: layers,
      axisEnds: ends,
      currentPoints: buildPolygonPoints(
        cx,
        cy,
        radius,
        count,
        skills.map((s) => s.current),
        maxLevel
      ),
      targetPoints: buildPolygonPoints(
        cx,
        cy,
        radius,
        count,
        skills.map((s) => s.target),
        maxLevel
      ),
    };
  }, [cx, cy, radius, count, maxLevel, skills]);

  return (
    <svg
      viewBox={`0 0 ${size} ${size}`}
      className="h-auto w-full"
      role="img"
      aria-label="技能雷达图"
    >
      {/* 背景网格：从内到外 maxLevel 层正多边形 */}
      {gridLayers.map((points, i) => (
        <polygon
          key={i}
          points={points}
          fill="none"
          stroke="currentColor"
          strokeOpacity={0.12}
          strokeWidth={1}
        />
      ))}

      {/* 坐标轴：从中心到每个技能端点 */}
      {axisEnds.map((end, i) => (
        <line
          key={i}
          x1={cx}
          y1={cy}
          x2={end.x}
          y2={end.y}
          stroke="currentColor"
          strokeOpacity={0.1}
          strokeWidth={1}
        />
      ))}

      {/* 目标能力多边形（虚线轮廓） */}
      <polygon
        points={targetPoints}
        fill="rgba(14,165,233,0.08)"
        stroke="#0ea5e9"
        strokeWidth={1.5}
        strokeDasharray="4 3"
      />

      {/* 当前能力多边形（实线填充） */}
      <polygon
        points={currentPoints}
        fill="rgba(16,185,129,0.18)"
        stroke="#10b981"
        strokeWidth={2}
      />

      {/* 当前能力顶点圆点 + 标签 + tooltip 触发区 */}
      {skills.map((skill, i) => {
        const angle = (360 / count) * i;
        const r = (skill.current / maxLevel) * radius;
        const { x, y } = polarToCartesian(cx, cy, r, angle);
        const labelPos = polarToCartesian(cx, cy, radius + 18, angle);
        const isHover = hoverIndex === i;

        return (
          <g key={skill.name}>
            {/* 技能标签 */}
            <text
              x={labelPos.x}
              y={labelPos.y}
              textAnchor="middle"
              dominantBaseline="middle"
              className="fill-zinc-600 dark:fill-zinc-300"
              style={{ fontSize: 11, fontWeight: isHover ? 700 : 500 }}
            >
              {skill.name}
            </text>

            {/* 顶点圆点 */}
            <circle
              cx={x}
              cy={y}
              r={isHover ? 5 : 3.5}
              fill="#10b981"
              stroke="white"
              strokeWidth={1.5}
            />

            {/* 透明热区，便于 hover */}
            <circle
              cx={x}
              cy={y}
              r={14}
              fill="transparent"
              onMouseEnter={() => setHoverIndex(i)}
              onMouseLeave={() => setHoverIndex(null)}
              style={{ cursor: "pointer" }}
            />

            {/* tooltip：当前/目标 */}
            {isHover && (
              <g pointerEvents="none">
                <rect
                  x={x + 8}
                  y={y - 22}
                  width={92}
                  height={36}
                  rx={4}
                  fill="rgba(0,0,0,0.85)"
                />
                <text
                  x={x + 14}
                  y={y - 8}
                  fill="#fff"
                  style={{ fontSize: 11 }}
                >
                  {skill.name} {skill.current}/{skill.target}
                </text>
                <text
                  x={x + 14}
                  y={y + 6}
                  fill="#9ca3af"
                  style={{ fontSize: 10 }}
                >
                  gap {skill.target - skill.current}
                </text>
              </g>
            )}
          </g>
        );
      })}
    </svg>
  );
}
