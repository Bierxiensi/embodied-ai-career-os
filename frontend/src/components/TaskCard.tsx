"use client";

/** 任务卡片。
 *
 * Day7 改造：todo/doing 态任务增加"完成并复盘"按钮，点击展开 TaskCompleteForm。
 * done 态保持纯展示（含 evidence 链接）。
 *
 * 数据流：
 *   点击"完成并复盘" → 展开 TaskCompleteForm
 *   → 提交 → POST /api/reviewer/review
 *   → router.refresh() → Server Component 重新获取 → 雷达图刷新
 */

import { useState } from "react";

import type { Task, TaskStatus } from "@/types";
import TaskCompleteForm from "./TaskCompleteForm";

type Props = { tasks: Task[] };

// 状态徽章配置：集中管理三态样式
const STATUS_CONFIG: Record<TaskStatus, { label: string; className: string }> = {
  todo: {
    label: "Todo",
    className: "bg-zinc-100 text-zinc-600 dark:bg-zinc-800 dark:text-zinc-300",
  },
  doing: {
    label: "Doing",
    className: "bg-sky-100 text-sky-700 dark:bg-sky-950 dark:text-sky-400",
  },
  done: {
    label: "Done",
    className: "bg-emerald-100 text-emerald-700 dark:bg-emerald-950 dark:text-emerald-400",
  },
};

export default function TaskCard({ tasks }: Props) {
  return (
    <section className="rounded-2xl border border-zinc-200 bg-white p-6 shadow-sm dark:border-zinc-800 dark:bg-zinc-950">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold text-black dark:text-zinc-50">
          ✅ Today&apos;s Tasks
        </h2>
        <span className="text-xs text-zinc-400 dark:text-zinc-600">
          {tasks.length} 项
        </span>
      </div>

      <ul className="mt-4 space-y-3">
        {tasks.map((task) => (
          <TaskItem key={task.id} task={task} />
        ))}
      </ul>
    </section>
  );
}

/** 单个任务：标题、关联技能、时长、验收清单、状态徽章、复盘入口。 */
function TaskItem({ task }: { task: Task }) {
  const config = STATUS_CONFIG[task.status];
  const [showForm, setShowForm] = useState(false);
  const isCompleted = task.status === "done";

  return (
    <li className="rounded-lg border border-zinc-100 p-3 dark:border-zinc-900">
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0">
          <p className="font-medium text-black truncate dark:text-zinc-50">
            {task.title}
          </p>
          <p className="mt-0.5 text-xs text-zinc-500 dark:text-zinc-400">
            {task.skill} · {task.duration} min
          </p>
        </div>
        <span className={`shrink-0 rounded-full px-2 py-0.5 text-xs font-medium ${config.className}`}>
          {config.label}
        </span>
      </div>

      {/* 验收标准清单：done 态勾选，其他态未勾选 */}
      <div className="mt-2">
        <p className="text-xs font-medium text-zinc-400 dark:text-zinc-600">
          Acceptance:
        </p>
        <ul className="mt-1 space-y-0.5 text-xs text-zinc-600 dark:text-zinc-400">
          {task.acceptance.map((item, i) => (
            <li key={i} className="flex items-start gap-1.5">
              <span className="text-zinc-400 dark:text-zinc-600">
                {isCompleted ? "✓" : "□"}
              </span>
              <span className={isCompleted ? "line-through opacity-60" : ""}>
                {item}
              </span>
            </li>
          ))}
        </ul>
      </div>

      {/* Day7：未完成任务显示"完成并复盘"按钮，点击展开表单 */}
      {!isCompleted && !showForm && (
        <button
          type="button"
          onClick={() => setShowForm(true)}
          className="mt-2 rounded-md border border-zinc-200 px-2.5 py-1 text-xs font-medium text-zinc-700 transition hover:bg-zinc-50 dark:border-zinc-700 dark:text-zinc-300 dark:hover:bg-zinc-800"
        >
          完成并复盘
        </button>
      )}

      {/* 展开复盘表单 */}
      {!isCompleted && showForm && (
        <TaskCompleteForm task={task} onCancel={() => setShowForm(false)} />
      )}
    </li>
  );
}
