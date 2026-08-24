"use client";

import { useState } from "react";
import type { Task } from "@/types";
import TaskCompleteForm from "./TaskCompleteForm";

type Props = {
  tasks: Task[];
};

const STATUS_CONFIG: Record<string, { label: string; className: string }> = {
  doing: { label: "进行中", className: "doing" },
  todo: { label: "待办", className: "todo" },
  done: { label: "已完成", className: "done" },
};

/** 今日任务卡片 — 显示任务列表，支持完成复盘交互。 */
export default function TodayTasks({ tasks }: Props) {
  const [activeFormIdx, setActiveFormIdx] = useState<number | null>(null);

  const doneCount = tasks.filter((t) => t.status === "done").length;

  return (
    <div
      className="flex flex-col"
      style={{
        flex: "1 1 420px",
        maxWidth: 690,
        minWidth: 0,
        gap: 18,
        padding: "var(--spacing-lg)",
        background: "var(--color-card)",
        border: "1px solid var(--color-hairline)",
        borderRadius: "var(--radius-card-lg)",
      }}
    >
      <div className="flex items-center justify-between">
        <span className="text-[17px] font-semibold" style={{ color: "var(--color-ink)" }}>
          今日任务
        </span>
        <span className="text-xs font-medium" style={{ color: "var(--color-ink-48)" }}>
          已规划 {tasks.length} 项 · 完成 {doneCount} 项
        </span>
      </div>

      {tasks.map((task, idx) => {
        const config = STATUS_CONFIG[task.status] ?? STATUS_CONFIG.todo;
        return (
          <div key={idx}>
            <div
              className="flex flex-col"
              style={{
                gap: 6,
                padding: "14px 16px",
                background: "#FAFAFB",
                borderRadius: "var(--radius-item-md)",
              }}
            >
              <div className="flex items-center justify-between">
                <span
                  className={`status-pill ${config.className}`}
                  style={{
                    display: "inline-flex",
                    alignItems: "center",
                    padding: "4px 10px",
                    borderRadius: "var(--radius-pill)",
                    fontSize: 11,
                    fontWeight: 600,
                    background:
                      config.className === "doing"
                        ? "var(--color-amber-soft)"
                        : config.className === "done"
                          ? "var(--color-emerald-soft)"
                          : "#F5F5F5",
                    color:
                      config.className === "doing"
                        ? "var(--color-amber-deep)"
                        : config.className === "done"
                          ? "var(--color-emerald-deep)"
                          : "var(--color-ink-32)",
                  }}
                >
                  {config.label}
                </span>
                <span className="text-xs font-medium" style={{ color: "var(--color-ink-48)" }}>
                  {task.duration ?? "预计 30 min"}
                </span>
              </div>
              <span className="text-[15px] font-semibold" style={{ color: "var(--color-ink)" }}>
                {task.title}
              </span>
              {task.acceptance && task.acceptance.length > 0 && (
                <span className="text-xs" style={{ color: "var(--color-ink-48)" }}>
                  验收 · {task.acceptance.join("  ·  ")}
                </span>
              )}
              {task.status !== "done" && (
                <button
                  onClick={() => setActiveFormIdx(activeFormIdx === idx ? null : idx)}
                  className="mt-1 self-start border-none text-xs font-medium"
                  style={{
                    color: "var(--color-primary)",
                    background: "transparent",
                    cursor: "pointer",
                  }}
                >
                  {activeFormIdx === idx ? "取消" : "完成并复盘 →"}
                </button>
              )}
            </div>
            {activeFormIdx === idx && task.status !== "done" && (
              <div className="mt-2">
                <TaskCompleteForm
                  task={task}
                  onCancel={() => setActiveFormIdx(null)}
                />
              </div>
            )}
          </div>
        );
      })}

      {tasks.length === 0 && (
        <div className="py-8 text-center text-sm" style={{ color: "var(--color-ink-48)" }}>
          暂无任务，点击上方「生成今日任务」开始
        </div>
      )}
    </div>
  );
}
