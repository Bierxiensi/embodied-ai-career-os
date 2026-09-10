"use client";

import { useState } from "react";
import type { Task } from "@/types";
import TaskCompleteForm from "./TaskCompleteForm";

type Props = {
  /** 当前视角的任务（已按赛道过滤） */
  tasks: Task[];
  /** 当前视角赛道名，用于标题说明"这一列是给哪条赛道排的" */
  trackName?: string | null;
  /** 全量任务数（跨赛道）—— 用于对比，避免用户以为数据丢了 */
  totalCount?: number;
};

const STATUS_CONFIG: Record<string, { label: string; className: string }> = {
  doing: { label: "进行中", className: "doing" },
  todo: { label: "待办", className: "todo" },
  done: { label: "已完成", className: "done" },
};

/** 任务列表卡片 — 显示**当前视角**的任务池，支持完成复盘交互。
 *
 * 2026-09-10 修复「任务没有跟随不同的角色看板走」：
 *   数据来自 `getTasks({ trackKey })`（Dashboard 传入），切视角即换列表。
 *   卡片标题栏把口径写清：`本视角 N 项 · 全量 M 项 · 完成 K 项`，
 *   这样即便某赛道任务少，你也能分辨是"真没有"而不是"数据丢了"。
 *
 * 历史修正保留：
 *   1. 原名「今日任务」名不副实（数据是全量、无"今日"过滤）→ 改叫「任务」
 *   2. `key={idx}` + `activeFormIdx` 都用数组下标 → 重复项会展开错卡片，
 *      改用 `task.id`
 *   3. 时长直接渲染裸数字 → 补 `min` 单位
 */
export default function TodayTasks({ tasks, trackName, totalCount }: Props) {
  const [activeTaskId, setActiveTaskId] = useState<string | null>(null);

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
      <div className="flex items-start justify-between" style={{ gap: 12 }}>
        <div className="flex flex-col" style={{ gap: 4 }}>
          <span
            className="text-[17px] font-semibold"
            style={{ color: "var(--color-ink)" }}
          >
            任务
          </span>
          {trackName && (
            <span className="text-xs" style={{ color: "var(--color-ink-48)" }}>
              当前视角 · {trackName}
            </span>
          )}
        </div>
        <span
          className="shrink-0 text-right text-xs font-medium"
          style={{ color: "var(--color-ink-48)", lineHeight: 1.7 }}
        >
          本视角 {tasks.length} 项 · 完成 {doneCount} 项
          {totalCount !== undefined && totalCount !== tasks.length && (
            <>
              <br />
              <span style={{ color: "var(--color-ink-32)" }}>
                全量任务池 {totalCount} 项
              </span>
            </>
          )}
        </span>
      </div>

      {tasks.map((task) => {
        const config = STATUS_CONFIG[task.status] ?? STATUS_CONFIG.todo;
        const isOpen = activeTaskId === task.id;
        return (
          <div key={task.id}>
            <div
              className="flex flex-col"
              style={{
                gap: 6,
                padding: "14px 16px",
                background: "#FAFAFB",
                borderRadius: "var(--radius-item-md)",
              }}
            >
              <div className="flex items-center justify-between" style={{ gap: 12 }}>
                <div className="flex items-center" style={{ gap: 8, minWidth: 0 }}>
                  <span
                    className={`status-pill ${config.className}`}
                    style={{
                      display: "inline-flex",
                      alignItems: "center",
                      padding: "3px 9px",
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
                  {/* 技能标签：说明这条任务在补哪个技能 */}
                  {task.skill && (
                    <span
                      className="inline-flex items-center"
                      style={{
                        padding: "3px 9px",
                        borderRadius: "var(--radius-pill)",
                        fontSize: 11,
                        fontWeight: 600,
                        background: "var(--color-primary-soft)",
                        color: "var(--color-primary)",
                      }}
                    >
                      {task.skill}
                    </span>
                  )}
                </div>
                <span
                  className="shrink-0 text-xs font-medium"
                  style={{ color: "var(--color-ink-48)" }}
                >
                  {task.duration && task.duration > 0 ? `${task.duration} min` : "未估时"}
                </span>
              </div>
              <span
                className="text-[15px] font-semibold"
                style={{ color: "var(--color-ink)" }}
              >
                {task.title}
              </span>
              {task.acceptance && task.acceptance.length > 0 && (
                <span className="text-xs" style={{ color: "var(--color-ink-48)" }}>
                  验收 · {task.acceptance.join("  ·  ")}
                </span>
              )}
              {task.status !== "done" && (
                <button
                  onClick={() => setActiveTaskId(isOpen ? null : task.id)}
                  className="mt-1 self-start border-none text-xs font-medium"
                  style={{
                    color: "var(--color-primary)",
                    background: "transparent",
                    cursor: "pointer",
                  }}
                >
                  {isOpen ? "取消" : "完成并复盘 →"}
                </button>
              )}
            </div>
            {isOpen && task.status !== "done" && (
              <div className="mt-2">
                <TaskCompleteForm
                  task={task}
                  onCancel={() => setActiveTaskId(null)}
                />
              </div>
            )}
          </div>
        );
      })}

      {tasks.length === 0 && (
        <div
          className="flex flex-col items-center"
          style={{ gap: 6, padding: "32px 16px" }}
        >
          <span className="text-sm font-medium" style={{ color: "var(--color-ink)" }}>
            本视角还没有任务
          </span>
          <span
            className="text-center text-xs"
            style={{ color: "var(--color-ink-48)", lineHeight: 1.6 }}
          >
            点右上角「生成今日任务」，Planner 会按
            {trackName ? `「${trackName}」` : "当前视角"}
            的硬性技能挑一个缺口最大的来规划。
          </span>
        </div>
      )}
    </div>
  );
}
