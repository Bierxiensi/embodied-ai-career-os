import type { Milestone, Project } from "@/types";
import Link from "next/link";

const STATUS_MAP: Record<string, { label: string; bg: string; color: string }> = {
  active: {
    label: "进行中",
    bg: "var(--color-emerald-soft)",
    color: "var(--color-emerald-deep)",
  },
  paused: {
    label: "已暂停",
    bg: "var(--color-amber-soft)",
    color: "var(--color-amber-deep)",
  },
  completed: { label: "已完成", bg: "#F5F5F5", color: "var(--color-ink-32)" },
};

/** 里程碑状态 → 徽章配色（与 ProjectProgressCard / MilestoneTimeline 同一套口径）。 */
export function milestoneBadge(status: Milestone["status"]): {
  bg: string;
  color: string;
} {
  switch (status) {
    case "completed":
      return { bg: "var(--color-emerald-soft)", color: "var(--color-emerald-deep)" };
    case "in_progress":
      return { bg: "var(--color-primary-soft)", color: "var(--color-primary)" };
    case "needs_baseline":
      return { bg: "var(--color-amber-soft)", color: "var(--color-amber-deep)" };
    default:
      return { bg: "#F5F5F5", color: "var(--color-ink-32)" };
  }
}

/** 选中"当前应关注的里程碑"：优先进行中 / 待生成 baseline，否则取第一个未解锁的。
 *
 * 抽出来给 ProjectCard 与 ProjectProgressCard 共用 —— 两处曾各自实现，
 * 且都在拿不到 milestones 时兜底成"全部完成"（0/7 的项目也这么写，是错的）。
 */
export function pickCurrentMilestone(project: Project) {
  return (
    project.milestones.find(
      (m) => m.status === "in_progress" || m.status === "needs_baseline"
    ) ?? project.milestones.find((m) => m.status === "locked")
  );
}

/** 当前里程碑的一句话描述（对空数组/全部完成做诚实降级）。 */
export function describeCurrentMilestone(project: Project): string {
  const current = pickCurrentMilestone(project);
  const total = project.milestoneTotal ?? 0;
  const done = project.milestoneCompleted ?? 0;

  if (current) {
    const isActive =
      current.status === "in_progress" || current.status === "needs_baseline";
    return isActive
      ? `当前 · ${current.version} ${current.title}`
      : `下一步 · ${current.version} ${current.title}`;
  }
  if (total === 0) return "暂无里程碑";
  if (done === total) return "全部里程碑已完成";
  return "暂无进行中的里程碑";
}

/** 项目卡片 —— 设计系统配色（card / hairline / ink token）。
 *
 * 2026-09-10 重写：原实现用 `border-zinc-200 bg-white dark:bg-zinc-950`
 * 这类 Tailwind 直出配色，与全站 `var(--color-*)` token 体系不一致，
 * 在暗色 token 下会对不上（token 已定义暗色值，写死的 zinc 不会跟随）。
 */
export default function ProjectCard({ project }: { project: Project }) {
  const status = STATUS_MAP[project.status] ?? STATUS_MAP.active;
  const pct = project.progressPct ?? 0;
  const total = project.milestoneTotal ?? 0;
  const done = project.milestoneCompleted ?? 0;
  const currentLabel = describeCurrentMilestone(project);

  return (
    <Link
      href={`/projects/${project.id}`}
      className="flex flex-col no-underline"
      style={{
        gap: 14,
        padding: "var(--spacing-lg)",
        background: "var(--color-card)",
        border: "1px solid var(--color-hairline)",
        borderRadius: "var(--radius-card-lg)",
      }}
    >
      {/* 标题行 */}
      <div className="flex items-start justify-between" style={{ gap: 16 }}>
        <div className="flex flex-col" style={{ gap: 6, minWidth: 0 }}>
          <span
            className="text-[17px] font-semibold"
            style={{ color: "var(--color-ink)" }}
          >
            {project.name}
          </span>
          <span className="text-[13px]" style={{ color: "var(--color-ink-48)" }}>
            {project.goal}
          </span>
        </div>
        <span
          className="inline-flex shrink-0 items-center"
          style={{
            padding: "4px 10px",
            borderRadius: "var(--radius-pill)",
            fontSize: 11,
            fontWeight: 600,
            background: status.bg,
            color: status.color,
          }}
        >
          {status.label}
        </span>
      </div>

      {/* 进度条 */}
      <div className="flex flex-col" style={{ gap: 8 }}>
        <div
          className="w-full overflow-hidden"
          style={{
            height: 6,
            background: "var(--color-hairline-soft)",
            borderRadius: 3,
          }}
        >
          <div
            className="h-full"
            style={{
              width: `${pct}%`,
              background:
                project.status === "paused"
                  ? "var(--color-amber)"
                  : "var(--color-emerald)",
              borderRadius: 3,
            }}
          />
        </div>
        <div className="flex items-center justify-between">
          <span className="text-xs" style={{ color: "var(--color-ink-48)" }}>
            {currentLabel}
          </span>
          <span
            className="text-xs font-medium"
            style={{ color: "var(--color-ink-48)" }}
          >
            {done}/{total} · {pct}%
          </span>
        </div>
      </div>

      {/* 里程碑版本徽章 */}
      {total > 0 && (
        <div className="flex flex-wrap" style={{ gap: 6 }}>
          {project.milestones.slice(0, 8).map((m) => {
            const badge = milestoneBadge(m.status);
            return (
              <span
                key={m.id}
                title={`${m.version} ${m.title} · ${m.goal}`}
                className="inline-flex items-center"
                style={{
                  padding: "3px 9px",
                  borderRadius: "var(--radius-pill)",
                  fontSize: 11,
                  fontWeight: 600,
                  background: badge.bg,
                  color: badge.color,
                }}
              >
                {m.version}
              </span>
            );
          })}
          {project.milestones.length > 8 && (
            <span
              className="inline-flex items-center"
              style={{ fontSize: 11, color: "var(--color-ink-48)" }}
            >
              +{project.milestones.length - 8}
            </span>
          )}
        </div>
      )}
    </Link>
  );
}
