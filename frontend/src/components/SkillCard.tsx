import type { Skill } from "@/types";
import StarRating from "./StarRating";

/** 技能卡片。按分类分组展示技能等级、目标对比与能力证明。
 * Day3 用星级 + 进度条；Day4 将在此基础上加雷达图。
 */
type Props = { skills: Skill[] };

// 分类展示顺序：强项在前，弱项（目标岗位核心）在后
const CATEGORY_ORDER = ["Strong", "Medium", "Weak"] as const;

export default function SkillCard({ skills }: Props) {
  // 按分类分组，保持 Strong → Medium → Weak 顺序
  const grouped = CATEGORY_ORDER.map((cat) => ({
    category: cat,
    items: skills.filter((s) => s.category === cat),
  })).filter((g) => g.items.length > 0);

  return (
    <section className="rounded-2xl border border-zinc-200 bg-white p-6 shadow-sm dark:border-zinc-800 dark:bg-zinc-950">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold text-black dark:text-zinc-50">
          📊 Skills
        </h2>
        <span className="text-xs text-zinc-400 dark:text-zinc-600">
          {skills.length} 项
        </span>
      </div>

      <div className="mt-4 space-y-5">
        {grouped.map((group) => (
          <div key={group.category}>
            <p className="mb-2 text-xs font-medium tracking-wider text-zinc-400 uppercase dark:text-zinc-600">
              {group.category}
            </p>
            <ul className="space-y-3">
              {group.items.map((skill) => (
                <SkillItem key={skill.id} skill={skill} />
              ))}
            </ul>
          </div>
        ))}
      </div>
    </section>
  );
}

/** 单个技能行：名称、星级、当前/目标、达成进度、能力证明。 */
function SkillItem({ skill }: { skill: Skill }) {
  const percent =
    skill.targetLevel > 0
      ? Math.round((skill.level / skill.targetLevel) * 100)
      : 0;

  return (
    <li className="rounded-lg border border-zinc-100 p-3 dark:border-zinc-900">
      <div className="flex items-center justify-between">
        <span className="font-medium text-black dark:text-zinc-50">
          {skill.name}
        </span>
        <div className="flex items-center gap-2">
          <StarRating level={skill.level} />
          <span className="text-xs text-zinc-400 dark:text-zinc-600">
            {skill.level}/{skill.targetLevel}
          </span>
        </div>
      </div>

      {/* 达成度进度条 */}
      <div className="mt-2 h-1.5 w-full overflow-hidden rounded-full bg-zinc-100 dark:bg-zinc-800">
        <div
          className="h-full rounded-full bg-sky-500"
          style={{ width: `${percent}%` }}
        />
      </div>

      {/* 能力证明：弱项无证明时提示待补 */}
      {skill.evidence.length > 0 ? (
        <ul className="mt-2 space-y-0.5 text-xs text-zinc-500 dark:text-zinc-400">
          {skill.evidence.map((e, i) => (
            <li key={i}>· {e}</li>
          ))}
        </ul>
      ) : (
        <p className="mt-2 text-xs text-amber-600 dark:text-amber-500">
          待补充能力证明
        </p>
      )}
    </li>
  );
}
