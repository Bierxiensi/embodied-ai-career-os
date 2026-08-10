import type { Project } from "@/types";
import Link from "next/link";

const statusLabel: Record<string, string> = {
  active: "进行中",
  paused: "已暂停",
  completed: "已完成",
};

export default function ProjectCard({ project }: { project: Project }) {
  return (
    <Link
      href={`/projects/${project.id}`}
      className="block rounded-2xl border border-zinc-200 bg-white p-6 hover:shadow-md transition-shadow dark:border-zinc-800 dark:bg-zinc-950"
    >
      <div className="flex items-start justify-between">
        <div>
          <h3 className="text-lg font-semibold text-zinc-900 dark:text-zinc-100">
            {project.name}
          </h3>
          <p className="mt-1 text-sm text-zinc-500 dark:text-zinc-400">
            {project.goal}
          </p>
        </div>
        <span className="text-xs px-2 py-1 rounded-full bg-zinc-100 text-zinc-600 dark:bg-zinc-800 dark:text-zinc-400">
          {statusLabel[project.status] || project.status}
        </span>
      </div>

      <div className="mt-4 flex items-center gap-2">
        <div className="flex-1 h-2 bg-zinc-100 dark:bg-zinc-800 rounded-full overflow-hidden">
          <div
            className="h-full bg-blue-500 rounded-full transition-all"
            style={{ width: `${project.progressPct}%` }}
          />
        </div>
        <span className="text-sm font-medium text-zinc-600 dark:text-zinc-400">
          {project.progressPct}%
        </span>
      </div>

      <div className="mt-3 flex flex-wrap gap-1.5">
        {project.milestones.slice(0, 6).map((m) => (
          <span
            key={m.id}
            className={`text-xs px-1.5 py-0.5 rounded ${
              m.status === "completed"
                ? "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400"
                : m.status === "in_progress"
                ? "bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400"
                : "bg-zinc-100 text-zinc-400 dark:bg-zinc-800 dark:text-zinc-500"
            }`}
          >
            {m.version}
          </span>
        ))}
      </div>
    </Link>
  );
}
