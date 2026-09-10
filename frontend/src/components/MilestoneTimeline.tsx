"use client";

import type { Milestone, Skill } from "@/types";
import { projectService } from "@/services/projectService";
import { useRouter } from "next/navigation";
import { useState } from "react";

/** 状态 → 配色（与 ProjectCard.milestoneBadge 同一套 token 口径）。
 *
 * 2026-09-10 重写：原实现用 `text-green-600 dark:text-green-400`
 * 这类 Tailwind 直出配色 + `dark:` 变体，与全站 `var(--color-*)` token
 * 体系不一致（token 自己已定义暗色值，`dark:` 会与之打架）。
 */
const STATUS_STYLE: Record<
  string,
  { label: string; bg: string; color: string; border: string; icon: string }
> = {
  completed: {
    label: "已完成",
    bg: "var(--color-emerald-soft)",
    color: "var(--color-emerald-deep)",
    border: "var(--color-hairline)",
    icon: "✓",
  },
  in_progress: {
    label: "进行中",
    bg: "var(--color-primary-soft)",
    color: "var(--color-primary)",
    border: "var(--color-primary)",
    icon: "●",
  },
  needs_baseline: {
    label: "待生成 baseline",
    bg: "var(--color-amber-soft)",
    color: "var(--color-amber-deep)",
    border: "var(--color-amber)",
    icon: "◐",
  },
  locked: {
    label: "未解锁",
    bg: "#F5F5F5",
    color: "var(--color-ink-32)",
    border: "var(--color-hairline)",
    icon: "○",
  },
};

type Props = {
  milestones: Milestone[];
  projectId: string;
  skills: { name: string; level: number; target: number }[];
  generatedMilestoneIds: string[];
};

export default function MilestoneTimeline({
  milestones,
  projectId,
  skills,
  generatedMilestoneIds,
}: Props) {
  const router = useRouter();
  const [generating, setGenerating] = useState<string | null>(null);

  const handleGenerateTasks = async (milestoneId: string) => {
    setGenerating(milestoneId);
    try {
      await projectService.generateTasks(milestoneId, {
        available_minutes: 120,
        skills,
      });
      // 标记 milestone 为 needs_baseline，触发引导流程
      await projectService.patchMilestone(milestoneId, {
        status: "needs_baseline",
      });
      router.refresh();
    } finally {
      setGenerating(null);
    }
  };

  const handleToggleStatus = async (m: Milestone) => {
    const nextStatus =
      m.status === "locked"
        ? "in_progress"
        : m.status === "in_progress"
          ? "completed"
          : m.status === "needs_baseline"
            ? "in_progress" // 点击回到 in_progress（允许重新生成）
            : m.status === "completed"
              ? "in_progress"
              : m.status;
    await projectService.patchMilestone(m.id, { status: nextStatus });
    router.refresh();
  };

  return (
    <div className="flex flex-col" style={{ gap: 10 }}>
      {milestones.map((m) => {
        const hasTasks = generatedMilestoneIds.includes(m.id);
        const style = STATUS_STYLE[m.status] ?? STATUS_STYLE.locked;
        const isActive = m.status === "in_progress" || m.status === "needs_baseline";

        return (
          <div
            key={m.id}
            className="flex flex-col"
            style={{
              gap: 10,
              padding: "14px 16px",
              background: isActive ? "var(--color-primary-soft)" : "#FAFAFB",
              border: `1px solid ${isActive ? style.border : "var(--color-hairline)"}`,
              borderRadius: "var(--radius-item-md)",
            }}
          >
            <div className="flex items-center justify-between" style={{ gap: 16 }}>
              <div className="flex items-center" style={{ gap: 12, minWidth: 0 }}>
                <button
                  type="button"
                  onClick={() => handleToggleStatus(m)}
                  className="shrink-0 cursor-pointer border-none"
                  style={{
                    width: 22,
                    height: 22,
                    borderRadius: "var(--radius-pill)",
                    background: style.bg,
                    color: style.color,
                    fontSize: 12,
                    fontWeight: 700,
                    lineHeight: 1,
                    cursor: "pointer",
                  }}
                  title={
                    m.status === "locked"
                      ? "解锁开始"
                      : m.status === "in_progress"
                        ? "标记完成"
                        : "重新打开"
                  }
                >
                  {style.icon}
                </button>
                <div className="flex flex-col" style={{ gap: 3, minWidth: 0 }}>
                  <div className="flex items-center" style={{ gap: 8 }}>
                    <span
                      className="text-[15px] font-semibold"
                      style={{ color: "var(--color-ink)" }}
                    >
                      {m.version} · {m.title}
                    </span>
                    <span
                      className="inline-flex shrink-0 items-center"
                      style={{
                        padding: "2px 8px",
                        borderRadius: "var(--radius-pill)",
                        fontSize: 10,
                        fontWeight: 600,
                        background: style.bg,
                        color: style.color,
                      }}
                    >
                      {style.label}
                    </span>
                  </div>
                  <span className="text-xs" style={{ color: "var(--color-ink-48)" }}>
                    {m.goal}
                  </span>
                </div>
              </div>

              {isActive && (
                <button
                  type="button"
                  onClick={() => handleGenerateTasks(m.id)}
                  disabled={
                    generating === m.id || hasTasks || m.status === "needs_baseline"
                  }
                  className="shrink-0 border-none"
                  style={{
                    padding: "6px 14px",
                    borderRadius: "var(--radius-pill)",
                    fontSize: 12,
                    fontWeight: 600,
                    background: "var(--color-primary)",
                    color: "var(--color-on-primary)",
                    border: "none",
                    cursor:
                      generating === m.id || hasTasks || m.status === "needs_baseline"
                        ? "not-allowed"
                        : "pointer",
                    opacity:
                      generating === m.id || hasTasks || m.status === "needs_baseline"
                        ? 0.5
                        : 1,
                  }}
                >
                  {generating === m.id
                    ? "生成中..."
                    : hasTasks || m.status === "needs_baseline"
                      ? "任务已生成"
                      : "生成任务"}
                </button>
              )}
            </div>

            {/* 脚手架详情：workspace 路径 + 必改项清单 */}
            {(m.workspace || (m.requiredModifications?.length ?? 0) > 0) && (
              <div
                className="flex flex-col"
                style={{
                  gap: 10,
                  paddingTop: 12,
                  borderTop: "1px solid var(--color-hairline)",
                }}
              >
                {m.workspace && (
                  <div
                    className="font-mono text-xs"
                    style={{ color: "var(--color-ink-48)" }}
                  >
                    📁 {m.workspace}
                  </div>
                )}
                {m.requiredModifications && m.requiredModifications.length > 0 && (
                  <ul className="flex flex-col" style={{ gap: 8, margin: 0, padding: 0 }}>
                    {m.requiredModifications.map((mod, i) => (
                      <li
                        key={`${mod.title}-${i}`}
                        className="flex flex-col"
                        style={{
                          gap: 4,
                          listStyle: "none",
                          padding: "10px 12px",
                          background: "var(--color-card)",
                          borderRadius: "var(--radius-item-sm)",
                        }}
                      >
                        <span
                          className="text-xs font-semibold"
                          style={{ color: "var(--color-ink)" }}
                        >
                          ✏️ 必改项 {i + 1}：{mod.title}
                        </span>
                        <span
                          className="text-xs"
                          style={{ color: "var(--color-ink-48)" }}
                        >
                          {mod.goal}
                        </span>
                        {mod.files?.length > 0 && (
                          <span
                            className="font-mono text-[11px]"
                            style={{ color: "var(--color-ink-32)" }}
                          >
                            {mod.files.join(" · ")}
                          </span>
                        )}
                        {mod.verification && (
                          <code
                            className="block font-mono text-[11px]"
                            style={{
                              marginTop: 2,
                              padding: "6px 8px",
                              background: "var(--color-primary-soft)",
                              color: "var(--color-primary)",
                              borderRadius: "var(--radius-item-sm)",
                            }}
                          >
                            {mod.verification}
                          </code>
                        )}
                      </li>
                    ))}
                  </ul>
                )}
              </div>
            )}

            {/* needs_baseline 引导：去 Claude Code 生成 baseline */}
            {m.status === "needs_baseline" && !m.workspace && (
              <div
                className="flex items-start"
                style={{
                  gap: 10,
                  padding: "10px 12px",
                  background: "var(--color-amber-soft)",
                  borderRadius: "var(--radius-item-sm)",
                }}
              >
                <span
                  className="text-sm"
                  style={{ color: "var(--color-amber-deep)" }}
                >
                  ⏳
                </span>
                <div className="flex flex-col" style={{ gap: 2 }}>
                  <span
                    className="text-xs font-semibold"
                    style={{ color: "var(--color-amber-deep)" }}
                  >
                    Baseline 待生成
                  </span>
                  <span
                    className="text-xs"
                    style={{ color: "var(--color-amber-deep)", opacity: 0.85 }}
                  >
                    在 Claude Code 说「开始 {m.version}」，AI 会生成参考代码并回退核心逻辑供你练习。
                  </span>
                </div>
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}
