import ProjectCard from "@/components/ProjectCard";
import { projectService } from "@/services/projectService";
import Link from "next/link";

export const dynamic = "force-dynamic";

export default async function ProjectsPage() {
  const projects = await projectService.list();

  return (
    <main className="min-h-full bg-zinc-50 dark:bg-black">
      <div className="mx-auto max-w-3xl px-6 py-10">
        <header className="mb-8 flex items-center justify-between">
          <div>
            <Link
              href="/dashboard"
              className="text-xs text-zinc-400 hover:text-zinc-600 dark:text-zinc-600 dark:hover:text-zinc-400"
            >
              ← Dashboard
            </Link>
            <h1 className="mt-1 text-2xl font-bold text-zinc-900 dark:text-zinc-100">
              项目实践
            </h1>
          </div>
        </header>

        {projects.length === 0 ? (
          <div className="rounded-2xl border border-dashed border-zinc-300 p-12 text-center dark:border-zinc-700">
            <p className="text-sm text-zinc-500 dark:text-zinc-400">
              还没有项目。通过 API 创建你的第一个实践项目。
            </p>
          </div>
        ) : (
          <div className="space-y-4">
            {projects.map((p) => (
              <ProjectCard key={p.id} project={p} />
            ))}
          </div>
        )}
      </div>
    </main>
  );
}
