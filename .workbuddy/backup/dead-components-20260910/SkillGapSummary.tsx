import type { RadarSkill } from "./RadarChart";

/** 技能缺口汇总。
 * 计算 Robot AI Engineer 岗位 Ready 度，并列出最大缺口，
 * 直接服务未来 Planner Agent（Agent 可读取最大 gap 生成学习任务）。
 */
type Props = {
  skills: RadarSkill[];
};

export default function SkillGapSummary({ skills }: Props) {
  // 计算总体 Ready 度：当前总分 / 目标总分
  const totalCurrent = skills.reduce((sum, s) => sum + s.current, 0);
  const totalTarget = skills.reduce((sum, s) => sum + s.target, 0);
  const readiness =
    totalTarget > 0 ? Math.round((totalCurrent / totalTarget) * 100) : 0;
  const gap = 100 - readiness;

  // 按缺口降序取前 3 大缺口
  const biggestGaps = [...skills]
    .map((s) => ({ name: s.name, gap: s.target - s.current }))
    .sort((a, b) => b.gap - a.gap)
    .slice(0, 3);

  return (
    <div className="space-y-4">
      {/* Ready 度环形进度 */}
      <div>
        <div className="flex items-baseline justify-between">
          <span className="text-sm font-medium text-black dark:text-zinc-50">
            Robot AI Readiness
          </span>
          <span className="text-2xl font-bold text-emerald-600 dark:text-emerald-400">
            {readiness}%
          </span>
        </div>
        <div className="mt-2 h-2.5 w-full overflow-hidden rounded-full bg-zinc-100 dark:bg-zinc-800">
          <div
            className="h-full rounded-full bg-emerald-500 transition-all"
            style={{ width: `${readiness}%` }}
          />
        </div>
        <p className="mt-1 text-xs text-zinc-400 dark:text-zinc-600">
          当前 {totalCurrent} / 目标 {totalTarget} · 缺口 {gap}%
        </p>
      </div>

      {/* 最大缺口列表：未来 Planner Agent 的输入信号 */}
      <div>
        <p className="mb-2 text-xs font-medium tracking-wider text-zinc-400 uppercase dark:text-zinc-600">
          Biggest Gap
        </p>
        <ol className="space-y-1.5">
          {biggestGaps.map((item, i) => (
            <li
              key={item.name}
              className="flex items-center justify-between rounded-md bg-zinc-50 px-2.5 py-1.5 dark:bg-zinc-900"
            >
              <span className="flex items-center gap-2 text-sm text-black dark:text-zinc-50">
                <span className="text-xs text-zinc-400 dark:text-zinc-600">
                  {i + 1}.
                </span>
                {item.name}
              </span>
              <span className="text-xs font-medium text-red-500">
                -{item.gap}
              </span>
            </li>
          ))}
        </ol>
      </div>
    </div>
  );
}
