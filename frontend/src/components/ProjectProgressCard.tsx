import Link from "next/link";
import type { Project } from "@/types";
import { describeCurrentMilestone } from "./ProjectCard";

type Props = {
  projects: Project[];
};

const STATUS_MAP: Record<string, { label: string; bg: string; color: string }> = {
  active: { label: "进行中", bg: "var(--color-emerald-soft)", color: "var(--color-emerald-deep)" },
  paused: { label: "已暂停", bg: "var(--color-amber-soft)", color: "var(--color-amber-deep)" },
  completed: { label: "已完成", bg: "#F5F5F5", color: "var(--color-ink-32)" },
};

/** 项目进度卡片 — 显示项目列表及当前里程碑进度。 */
export default function ProjectProgressCard({ projects }: Props) {
  if (projects.length === 0) return null;

  const activeCount = projects.filter((p) => p.status === "active").length;
  const pausedCount = projects.filter((p) => p.status === "paused").length;

  return (
    <div
      className="flex flex-1 flex-col"
      style={{
        gap: 18,
        padding: "var(--spacing-lg)",
        background: "var(--color-card)",
        border: "1px solid var(--color-hairline)",
        borderRadius: "var(--radius-card-lg)",
      }}
    >
      <div className="flex items-center justify-between">
        <span className="text-[17px] font-semibold" style={{ color: "var(--color-ink)" }}>
          项目进度
        </span>
        <span className="text-xs font-medium" style={{ color: "var(--color-ink-48)" }}>
          {activeCount} 个进行中{pausedCount > 0 ? ` · ${pausedCount} 个暂停` : ""}
        </span>
      </div>

      {projects.slice(0, 2).map((project) => {
        const status = STATUS_MAP[project.status] ?? STATUS_MAP.active;
        const pct = project.progressPct ?? 0;

        return (
          <Link
            key={project.id}
            href={`/projects/${project.id}`}
            className="flex flex-col no-underline"
            style={{
              gap: 10,
              padding: "14px 16px",
              background: "#FAFAFB",
              borderRadius: "var(--radius-item-md)",
            }}
          >
            <div className="flex items-center justify-between">
              <span className="text-[15px] font-semibold" style={{ color: "var(--color-ink)" }}>
                {project.name}
              </span>
              <span
                className="inline-flex items-center"
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
            <div
              className="w-full overflow-hidden"
              style={{
                height: 6,
                background: "#E8E8ED",
                borderRadius: 3,
              }}
            >
              <div
                className="h-full"
                style={{
                  width: `${pct}%`,
                  background: project.status === "paused" ? "var(--color-amber)" : "var(--color-emerald)",
                  borderRadius: 3,
                }}
              />
            </div>
            <span className="text-xs" style={{ color: "var(--color-ink-48)" }}>
              {describeCurrentMilestone(project)} · {pct}%
            </span>
          </Link>
        );
      })}
    </div>
  );
}
