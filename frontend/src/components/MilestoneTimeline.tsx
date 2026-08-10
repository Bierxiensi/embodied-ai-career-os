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
};

export default function MilestoneTimeline({
  milestones,
  projectId,
  skills,
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
      m.status === "in_progress"
        ? "completed"
        : m.status === "completed"
        ? "in_progress"
        : m.status;
    await projectService.patchMilestone(m.id, { status: nextStatus });
    router.refresh();
  };

  return (
    <div className="space-y-1">
      {milestones.map((m) => (
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
                title={m.status === "in_progress" ? "标记完成" : "标记进行中"}
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
                disabled={generating === m.id}
                className="text-xs px-3 py-1.5 rounded-lg bg-blue-600 text-white hover:bg-blue-700 disabled:opacity-50 transition-colors"
              >
                {generating === m.id ? "生成中..." : "生成任务"}
              </button>
            )}
          </div>
        </div>
      ))}
    </div>
  );
}
