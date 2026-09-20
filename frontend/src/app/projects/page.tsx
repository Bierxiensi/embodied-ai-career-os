/** 项目实践列表页（Server Component）。 */

import ProjectCard from "@/components/ProjectCard";
import PageShell from "@/ui/page-shell";
import ErrorCard from "@/ui/error-card";
import { projectService } from "@/services/projectService";

export const dynamic = "force-dynamic";

export default async function ProjectsPage() {
  try {
    const projects = await projectService.list();
    const activeCount = projects.filter((p) => p.status === "active").length;

    return (
      <PageShell
        eyebrow="PROJECTS · 实践项目"
        title="项目实践"
        subtitle={`把学习落到真实可交付的产物上 · ${projects.length} 个项目${
          activeCount > 0 ? ` · ${activeCount} 个进行中` : ""
        }`}
      >
        {projects.length === 0 ? (
          <div
            className="flex flex-col items-center"
            style={{
              gap: 8,
              padding: "56px 24px",
              background: "var(--color-card)",
              border: "1px dashed var(--color-hairline)",
              borderRadius: "var(--radius-card-lg)",
            }}
          >
            <span
              className="text-[15px] font-semibold"
              style={{ color: "var(--color-ink)" }}
            >
              还没有项目
            </span>
            <span className="text-sm" style={{ color: "var(--color-ink-48)" }}>
              通过 API 创建你的第一个实践项目：
              <code
                className="ml-1 font-mono"
                style={{ color: "var(--color-primary)" }}
              >
                POST /api/projects
              </code>
            </span>
          </div>
        ) : (
          <div
            className="grid"
            style={{
              gap: "var(--spacing-lg)",
              gridTemplateColumns: "repeat(auto-fill, minmax(380px, 1fr))",
            }}
          >
            {projects.map((p) => (
              <ProjectCard key={p.id} project={p} />
            ))}
          </div>
        )}
      </PageShell>
    );
  } catch (err) {
    return <ErrorCard pageName="项目页" error={err} />;
  }
}
