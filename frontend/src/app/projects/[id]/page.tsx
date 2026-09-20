/** 项目详情页（Server Component）。
 *
 * 2026-09-10 重写：与列表页同一套设计系统（PageHeader + token 配色），
 * 顶栏由 app/layout.tsx 统一渲染。
 *
 * 数据：项目 + 里程碑 + 关联任务 + README 骨架（并行拉取，README 失败不击穿整页）。
 * 交互：MilestoneTimeline（客户端）负责里程碑状态切换与任务生成；
 *       ReadmeDraftCard（客户端）负责 README 预览 / 重新生成 / 保存 / 下载。
 */

import PageHeader from "@/components/PageHeader";
import MilestoneTimeline from "@/components/MilestoneTimeline";
import ReadmeDraftCard from "@/components/ReadmeDraftCard";
import { milestoneBadge } from "@/components/ProjectCard";
import ErrorCard from "@/ui/error-card";
import { getProjectReadme } from "@/services/packagingService";
import { projectService } from "@/services/projectService";
import { getSkills } from "@/services/skillService";
import { getTasks } from "@/services/taskService";

export const dynamic = "force-dynamic";

const STATUS_LABEL: Record<string, string> = {
  active: "进行中",
  paused: "已暂停",
  completed: "已完成",
};

const TASK_STATUS: Record<string, { label: string; bg: string; color: string }> = {
  done: {
    label: "已完成",
    bg: "var(--color-emerald-soft)",
    color: "var(--color-emerald-deep)",
  },
  doing: {
    label: "进行中",
    bg: "var(--color-amber-soft)",
    color: "var(--color-amber-deep)",
  },
  todo: { label: "待办", bg: "var(--color-zinc-100)", color: "var(--color-ink-32)" },
};

export default async function ProjectDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;

  try {
    const [project, skills, allTasks, readme] = await Promise.all([
      projectService.get(id),
      getSkills().catch(() => []),
      getTasks(id).catch(() => []),
      getProjectReadme(id).catch(() => null),
    ]);

    const status = milestoneBadge;
    const pct = project.progressPct ?? 0;

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
          eyebrow={`PROJECT · ${project.currentVersion}`}
          title={project.name}
          subtitle={project.goal}
          backHref="/projects"
          backLabel="项目列表"
          actions={
            <span
              className="inline-flex items-center"
              style={{
                padding: "5px 12px",
                borderRadius: "var(--radius-pill)",
                fontSize: 12,
                fontWeight: 600,
                background:
                  project.status === "active"
                    ? "var(--color-emerald-soft)"
                    : project.status === "paused"
                      ? "var(--color-amber-soft)"
                      : "var(--color-zinc-100)",
                color:
                  project.status === "active"
                    ? "var(--color-emerald-deep)"
                    : project.status === "paused"
                      ? "var(--color-amber-deep)"
                      : "var(--color-ink-32)",
              }}
            >
              {STATUS_LABEL[project.status] ?? project.status}
            </span>
          }
        >
          {/* 进度 */}
          <div
            className="flex items-center"
            style={{ gap: 12, paddingTop: 4, maxWidth: 520 }}
          >
            <div
              className="flex-1 overflow-hidden"
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
            <span
              className="text-xs font-medium"
              style={{ color: "var(--color-ink-48)" }}
            >
              {project.milestoneCompleted}/{project.milestoneTotal} 里程碑 · {pct}%
            </span>
          </div>
        </PageHeader>

        {/* 项目说明 */}
        {project.description && (
          <Card title="说明">
            <p className="text-sm" style={{ color: "var(--color-ink-80)" }}>
              {project.description}
            </p>
            {project.githubUrl && (
              <a
                href={project.githubUrl}
                className="mt-3 self-start text-xs font-medium no-underline"
                style={{ color: "var(--color-primary)" }}
              >
                {project.githubUrl} ↗
              </a>
            )}
          </Card>
        )}

        {/* 里程碑时间线 */}
        <Card
          title="里程碑"
          hint={`${project.milestoneTotal} 个 · 点击左侧标记可切换状态`}
        >
          <div className="flex flex-wrap" style={{ gap: 6, marginBottom: 4 }}>
            {project.milestones.map((m) => {
              const badge = status(m.status);
              return (
                <span
                  key={m.id}
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
          </div>
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
        </Card>

        {/* README 骨架（从证据链生成）—— 项目的"成品出口" */}
        {readme && <ReadmeDraftCard projectId={id} initial={readme} />}

        {/* 关联任务 */}
        {allTasks.length > 0 && (
          <Card title="关联任务" hint={`${allTasks.length} 项`}>
            <div className="flex flex-col" style={{ gap: 8 }}>
              {allTasks.map((t) => {
                const cfg = TASK_STATUS[t.status] ?? TASK_STATUS.todo;
                return (
                  <div
                    key={t.id}
                    className="flex items-center"
                    style={{
                      gap: 12,
                      padding: "12px 14px",
                      background: "var(--color-item-bg)",
                      borderRadius: "var(--radius-item-md)",
                    }}
                  >
                    <span
                      className="inline-flex shrink-0 items-center"
                      style={{
                        padding: "3px 9px",
                        borderRadius: "var(--radius-pill)",
                        fontSize: 11,
                        fontWeight: 600,
                        background: cfg.bg,
                        color: cfg.color,
                      }}
                    >
                      {cfg.label}
                    </span>
                    <span
                      className="text-sm font-medium"
                      style={{ color: "var(--color-ink)" }}
                    >
                      {t.title}
                    </span>
                    {t.duration > 0 && (
                      <span
                        className="ml-auto shrink-0 text-xs"
                        style={{ color: "var(--color-ink-48)" }}
                      >
                        {t.duration} min
                      </span>
                    )}
                  </div>
                );
              })}
            </div>
          </Card>
        )}
      </div>
    </main>
  );
  } catch (err) {
    return <ErrorCard pageName="项目详情" error={err} />;
  }
}

/** 页内卡片容器 —— 与 Dashboard 卡片同口径（白底 + hairline + 18px 圆角）。 */
function Card({
  title,
  hint,
  children,
}: {
  title: string;
  hint?: string;
  children: React.ReactNode;
}) {
  return (
    <section
      className="flex flex-col"
      style={{
        gap: 16,
        padding: "var(--spacing-lg)",
        background: "var(--color-card)",
        border: "1px solid var(--color-hairline)",
        borderRadius: "var(--radius-card-lg)",
      }}
    >
      <div className="flex items-center justify-between">
        <span
          className="text-[17px] font-semibold"
          style={{ color: "var(--color-ink)" }}
        >
          {title}
        </span>
        {hint && (
          <span className="text-xs font-medium" style={{ color: "var(--color-ink-48)" }}>
            {hint}
          </span>
        )}
      </div>
      {children}
    </section>
  );
}
