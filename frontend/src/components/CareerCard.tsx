import type { Career } from "@/types";

/** 职业目标卡片。展示目标岗位、薪资、时间规划与整体达成度。 */
type Props = { career: Career };

export default function CareerCard({ career }: Props) {
  return (
    <section className="rounded-2xl border border-zinc-200 bg-white p-6 shadow-sm dark:border-zinc-800 dark:bg-zinc-950">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold text-black dark:text-zinc-50">
          🎯 Career
        </h2>
        <span className="text-xs text-zinc-400 dark:text-zinc-600">
          目标岗位
        </span>
      </div>

      <div className="mt-4">
        <p className="text-2xl font-bold tracking-tight text-black dark:text-zinc-50">
          {career.targetRole}
        </p>
        <p className="mt-1 text-sm text-zinc-500 dark:text-zinc-400">
          {career.salaryTarget.toLocaleString()}+ RMB / 月
        </p>
      </div>

      <div className="mt-4 flex items-center justify-between text-sm">
        <span className="text-zinc-500 dark:text-zinc-400">
          目标时间：{career.timeframe}
        </span>
        <span className="font-medium text-black dark:text-zinc-50">
          {career.progress}%
        </span>
      </div>

      {/* 整体达成度进度条 */}
      <div className="mt-2 h-2 w-full overflow-hidden rounded-full bg-zinc-100 dark:bg-zinc-800">
        <div
          className="h-full rounded-full bg-emerald-500 transition-all"
          style={{ width: `${career.progress}%` }}
        />
      </div>
    </section>
  );
}
