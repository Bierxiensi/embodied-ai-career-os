/** 项目实践列表页（Server Component）。
 *
 * 2026-09-10 重写：此前本页是全站唯一没有顶栏、且自带一套
 * `bg-zinc-50 / dark:bg-black` 旧配色的页面（用户反馈「项目界面和其他风格不一致」）。
 * 现在统一为：
 *   顶栏     → app/layout.tsx（全站单一来源）
 *   页头     → PageHeader（与 JobsBoard / Dashboard 同尺寸口径）
 *   卡片     → ProjectCard（设计 token，不再是 Tailwind 直出配色）
 *
 * 错误处理：与 dashboard / jobs 页一致，后端不可用时给降级提示而非白屏。
 */

import PageHeader from "@/components/PageHeader";
import ProjectCard from "@/components/ProjectCard";
import { ApiError } from "@/lib/apiClient";
import { projectService } from "@/services/projectService";

export const dynamic = "force-dynamic";

export default async function ProjectsPage() {
  try {
    const projects = await projectService.list();
    const activeCount = projects.filter((p) => p.status === "active").length;

    return (
      <main className="flex flex-1 flex-col">
        <div
          className="flex flex-col"
          style={{
            gap: "var(--spacing-lg)",
            padding: "36px clamp(20px, 8vw, 120px) 48px",
          }}
        >
          <PageHeader
            eyebrow="PROJECTS · 实践项目"
            title="项目实践"
            subtitle={`把学习落到真实可交付的产物上 · ${projects.length} 个项目${
              activeCount > 0 ? ` · ${activeCount} 个进行中` : ""
            }`}
          />

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
        </div>
      </main>
    );
  } catch (err) {
    const message =
      err instanceof ApiError
        ? err.message
        : "无法连接后端服务，请确认 FastAPI 已启动（127.0.0.1:8000）";

    return (
      <main className="flex flex-1 items-center justify-center">
        <div
          className="max-w-md text-center"
          style={{
            padding: 32,
            background: "var(--color-card)",
            border: "1px solid var(--color-rose)",
            borderRadius: "var(--radius-card-lg)",
          }}
        >
          <h1
            className="text-lg font-semibold"
            style={{ color: "var(--color-rose-deep)" }}
          >
            后端连接失败
          </h1>
          <p className="mt-2 text-sm" style={{ color: "var(--color-ink-48)" }}>
            {message}
          </p>
        </div>
      </main>
    );
  }
}
