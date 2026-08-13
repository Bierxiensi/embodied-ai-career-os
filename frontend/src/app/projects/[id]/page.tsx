import MilestoneTimeline from "@/components/MilestoneTimeline";
import { projectService } from "@/services/projectService";
import { getSkills } from "@/services/skillService";
import { getTasks } from "@/services/taskService";
import Link from "next/link";

export const dynamic = "force-dynamic";

export default async function ProjectDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  const [project, skills, allTasks] = await Promise.all([
    projectService.get(id),
    getSkills(),
    getTasks(id),
  ]);

  return (
    <main className="min-h-full bg-zinc-50 dark:bg-black">
      <div className="mx-auto max-w-3xl px-6 py-10">
        <header className="mb-8">
          <Link
            href="/projects"
            className="text-xs text-zinc-400 hover:text-zinc-600 dark:text-zinc-600 dark:hover:text-zinc-400"
          >
            ← 项目列表
          </Link>
          <div className="mt-2 flex items-start justify-between">
            <div>
              <h1 className="text-2xl font-bold text-zinc-900 dark:text-zinc-100">
                {project.name}
              </h1>
              <p className="mt-1 text-sm text-zinc-500 dark:text-zinc-400">
                {project.goal}
              </p>
            </div>
            <span
              className={`text-xs px-2 py-1 rounded-full ${
                project.status === "active"
                  ? "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400"
                  : "bg-zinc-100 text-zinc-600 dark:bg-zinc-800 dark:text-zinc-400"
              }`}
            >
              {project.status === "active" ? "进行中" : project.status}
            </span>
          </div>

          {/* 进度条 */}
          <div className="mt-4 flex items-center gap-3">
            <div className="flex-1 h-2 bg-zinc-100 dark:bg-zinc-800 rounded-full overflow-hidden">
              <div
                className="h-full bg-blue-500 rounded-full transition-all"
                style={{ width: `${project.progressPct}%` }}
              />
            </div>
            <span className="text-sm font-medium text-zinc-600 dark:text-zinc-400">
              {project.progressPct}% ({project.milestoneCompleted}/
              {project.milestoneTotal})
            </span>
          </div>
        </header>

        {/* 里程碑时间线 */}
        <section>
          <h2 className="text-sm font-semibold text-zinc-800 dark:text-zinc-200 mb-4">
            里程碑
          </h2>
          <MilestoneTimeline
            milestones={project.milestones}
            projectId={id}
            skills={skills.map((s) => ({
              name: s.name,
              level: s.level,
              target: s.targetLevel,
            }))}
            generatedMilestoneIds={allTasks
              .map((t) => t.milestoneId)
              .filter((x): x is string => x != null)}
          />
        </section>

        {/* 关联任务 */}
        {allTasks.length > 0 && (
          <section className="mt-8">
            <h2 className="text-sm font-semibold text-zinc-800 dark:text-zinc-200 mb-3">
              关联任务
            </h2>
            <div className="space-y-2">
              {allTasks.map((t) => (
                <div
                  key={t.id}
                  className="flex items-center gap-3 rounded-lg border border-zinc-200 p-3 dark:border-zinc-800"
                >
                  <span
                    className={`text-xs px-1.5 py-0.5 rounded ${
                      t.status === "done"
                        ? "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400"
                        : t.status === "doing"
                        ? "bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400"
                        : "bg-zinc-100 text-zinc-500 dark:bg-zinc-800 dark:text-zinc-400"
                    }`}
                  >
                    {t.status === "done" ? "✓" : t.status === "doing" ? "●" : "○"}
                  </span>
                  <span className="text-sm text-zinc-700 dark:text-zinc-300">
                    {t.title}
                  </span>
                </div>
              ))}
            </div>
          </section>
        )}
      </div>
    </main>
  );
}
