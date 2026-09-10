import type { Skill } from "@/types";
import RadarChart, { type RadarSkill } from "./RadarChart";
import SkillGapSummary from "./SkillGapSummary";

/** 技能总览容器：雷达图 + 缺口汇总。
 *
 * 职责：技能整体分析（全局视角）。
 * 解耦于 Dashboard：未来 Career 页、面试能力分析页、Agent 评估页均可复用。
 * 数据经 props 注入，Day6 接 API 时仅改数据来源，组件不变。
 */
type Props = {
  skills: Skill[];
};

// 图例配置：当前 vs 目标
const LEGEND = [
  { color: "bg-emerald-500", label: "Current" },
  { color: "bg-sky-500", label: "Target" },
];

export default function SkillOverview({ skills }: Props) {
  // Skill → RadarSkill 适配（RadarChart 只关心 current/target，不需 evidence）
  const radarSkills: RadarSkill[] = skills.map((s) => ({
    name: s.name,
    current: s.level,
    target: s.targetLevel,
  }));

  return (
    <section className="rounded-2xl border border-zinc-200 bg-white p-6 shadow-sm dark:border-zinc-800 dark:bg-zinc-950">
      <div className="mb-4 flex items-center justify-between">
        <h2 className="text-lg font-semibold text-black dark:text-zinc-50">
          📡 Robot AI Capability
        </h2>
        <div className="flex items-center gap-3">
          {LEGEND.map((item) => (
            <span
              key={item.label}
              className="flex items-center gap-1.5 text-xs text-zinc-500 dark:text-zinc-400"
            >
              <span className={`h-2 w-2 rounded-full ${item.color}`} />
              {item.label}
            </span>
          ))}
        </div>
      </div>

      {/* 雷达图与缺口汇总两栏：宽屏并排，窄屏堆叠 */}
      <div className="grid grid-cols-1 items-center gap-6 md:grid-cols-2">
        <div className="text-zinc-300 dark:text-zinc-600">
          <RadarChart skills={radarSkills} />
        </div>
        <SkillGapSummary skills={radarSkills} />
      </div>
    </section>
  );
}
