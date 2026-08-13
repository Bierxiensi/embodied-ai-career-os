"use client";

import type { Milestone, Skill } from "@/types";
import { projectService } from "@/services/projectService";
import { useRouter } from "next/navigation";
import { useState } from "react";

const statusIcon: Record<string, string> = {
  completed: "✅",
  in_progress: "●",
  locked: "🔒",
};

const statusColor: Record<string, string> = {
  completed: "text-green-600 dark:text-green-400",
  in_progress: "text-blue-600 dark:text-blue-400",
  locked: "text-zinc-400 dark:text-zinc-500",
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
        : m.status === "completed"
        ? "in_progress"
        : m.status;
    await projectService.patchMilestone(m.id, { status: nextStatus });
    router.refresh();
  };

  return (
    <div className="space-y-1">
      {milestones.map((m) => {
        const hasTasks = generatedMilestoneIds.includes(m.id);
        return (
          <div
            key={m.id}
            className={`rounded-lg border p-4 ${
              m.status === "in_progress"
                ? "border-blue-200 bg-blue-50/50 dark:border-blue-900 dark:bg-blue-950/20"
                : "border-zinc-200 dark:border-zinc-800"
            }`}
          >
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <button
                  type="button"
                  onClick={() => handleToggleStatus(m)}
                  className="text-lg cursor-pointer"
                  title={
                    m.status === "locked"
                      ? "解锁开始"
                      : m.status === "in_progress"
                      ? "标记完成"
                      : "重新打开"
                  }
                >
                  {statusIcon[m.status] || "⬜"}
                </button>
                <div>
                  <span
                    className={`text-sm font-medium ${statusColor[m.status] || ""}`}
                  >
                    {m.version}: {m.title}
                  </span>
                  <p className="text-xs text-zinc-500 dark:text-zinc-400 mt-0.5">
                    {m.goal}
                  </p>
                </div>
              </div>
              {m.status === "in_progress" && (
                <button
                  type="button"
                  onClick={() => handleGenerateTasks(m.id)}
                  disabled={generating === m.id || hasTasks}
                  className="text-xs px-3 py-1.5 rounded-lg bg-blue-600 text-white hover:bg-blue-700 disabled:opacity-50 transition-colors"
                >
                  {generating === m.id
                    ? "生成中..."
                    : hasTasks
                    ? "任务已生成"
                    : "生成任务"}
                </button>
              )}
            </div>

            {/* 脚手架详情：workspace 路径 + 必改项清单 */}
            {(m.workspace || (m.requiredModifications?.length ?? 0) > 0) && (
              <div className="mt-3 border-t border-zinc-100 dark:border-zinc-800 pt-3 space-y-3">
                {m.workspace && (
                  <div className="text-xs font-mono text-zinc-600 dark:text-zinc-400">
                    📁 {m.workspace}
                  </div>
                )}
                {m.requiredModifications && m.requiredModifications.length > 0 && (
                  <ul className="space-y-2">
                    {m.requiredModifications.map((mod, i) => (
                      <li
                        key={i}
                        className="rounded-lg bg-white/60 dark:bg-zinc-900/40 p-2.5"
                      >
                        <div className="text-xs font-semibold text-zinc-800 dark:text-zinc-200">
                          ✏️ 必改项 {i + 1}: {mod.title}
                        </div>
                        <div className="text-xs text-zinc-500 dark:text-zinc-400 mt-0.5">
                          {mod.goal}
                        </div>
                        <code className="block text-[11px] font-mono text-blue-600 dark:text-blue-400 mt-1.5 bg-zinc-50 dark:bg-zinc-800 rounded px-1.5 py-1">
                          {mod.verification}
                        </code>
                      </li>
                    ))}
                  </ul>
                )}
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}
