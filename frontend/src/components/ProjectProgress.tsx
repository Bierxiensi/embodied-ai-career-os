"use client";

import type { Project } from "@/types";
import Link from "next/link";

export default function ProjectProgress({ projects }: { projects: Project[] }) {
  if (projects.length === 0) return null;

  return (
    <section>
      <div className="flex items-center justify-between mb-3">
        <h2 className="text-sm font-semibold text-zinc-800 dark:text-zinc-200">
          项目进度
        </h2>
        <Link
          href="/projects"
          className="text-xs text-blue-600 hover:underline dark:text-blue-400"
        >
          查看全部 →
        </Link>
      </div>
      <div className="space-y-3">
        {projects.slice(0, 2).map((p) => (
          <Link
            key={p.id}
            href={`/projects/${p.id}`}
            className="block rounded-xl border border-zinc-200 bg-white p-4 hover:border-zinc-300 dark:border-zinc-800 dark:bg-zinc-950 dark:hover:border-zinc-700 transition-colors"
          >
            <div className="flex items-center justify-between mb-2">
              <span className="text-sm font-medium text-zinc-900 dark:text-zinc-100">
                {p.name}
              </span>
              <span
                className={`text-xs px-2 py-0.5 rounded-full ${
                  p.status === "active"
                    ? "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400"
                    : p.status === "paused"
                    ? "bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400"
                    : "bg-zinc-100 text-zinc-600 dark:bg-zinc-800 dark:text-zinc-400"
                }`}
              >
                {p.status === "active" ? "进行中" : p.status === "paused" ? "已暂停" : "已完成"}
              </span>
            </div>
            <div className="flex items-center gap-2">
              <div className="flex-1 h-1.5 bg-zinc-100 dark:bg-zinc-800 rounded-full overflow-hidden">
                <div
                  className="h-full bg-blue-500 rounded-full transition-all"
                  style={{ width: `${p.progressPct}%` }}
                />
              </div>
              <span className="text-xs text-zinc-500 dark:text-zinc-400 min-w-[3ch] text-right">
                {p.progressPct}%
              </span>
            </div>
            <p className="mt-1.5 text-xs text-zinc-500 dark:text-zinc-400">
              {p.currentVersion}:{" "}
              {p.milestones.find((m) => m.status === "in_progress")?.title ||
                p.milestones.find((m) => m.status === "needs_baseline")?.title ||
                p.milestones.find((m) => m.status === "locked")?.title ||
                "全部完成"}
            </p>
          </Link>
        ))}
      </div>
    </section>
  );
}
