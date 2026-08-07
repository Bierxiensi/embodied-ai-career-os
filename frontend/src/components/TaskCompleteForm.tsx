"use client";

/** 任务完成复盘表单（Client Component）。
 *
 * Day7 闭环前端入口：
 *   点击"完成并复盘" → 展开表单 → 填写日志+artifact → 提交 → Reviewer Agent → 刷新
 *
 * 设计原则（遵循用户调整4：MVP）：
 * - 纯 textarea + 文本输入，无富文本/文件上传/多步骤 wizard
 * - 提示用户"反思关键词"和"artifact"能加分，引导产出高质量证据
 * - 提交后 router.refresh() 让 Server Component 重新拉取，技能雷达图实时变化
 */

import { useRouter } from "next/navigation";
import { useState } from "react";

import { ApiError } from "@/lib/apiClient";
import { reviewTask } from "@/services/reviewerService";
import type { Task } from "@/types";

type Props = {
  task: Task;
  /** 取消回调（收起表单）。 */
  onCancel: () => void;
};

/** 状态机：idle → submitting → success/error。 */
type State =
  | { kind: "idle" }
  | { kind: "submitting" }
  | { kind: "success"; message: string }
  | { kind: "error"; message: string };

export default function TaskCompleteForm({ task, onCancel }: Props) {
  const router = useRouter();
  const [content, setContent] = useState("");
  const [artifactUrl, setArtifactUrl] = useState("");
  const [duration, setDuration] = useState(String(task.duration || 30));
  const [state, setState] = useState<State>({ kind: "idle" });

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!content.trim()) {
      setState({ kind: "error", message: "请填写学习日志" });
      return;
    }

    setState({ kind: "submitting" });
    try {
      const result = await reviewTask({
        taskId: task.id,
        content: content.trim(),
        durationMinutes: duration ? Number(duration) : undefined,
        artifactUrl: artifactUrl.trim() || undefined,
      });

      const upgraded = result.assessment.newLevel > result.assessment.oldLevel;
      const message = upgraded
        ? `✓ ${result.updatedSkill.name} 等级 ${result.assessment.oldLevel} → ${result.assessment.newLevel}（证据得分 ${result.assessment.evidenceScore}）`
        : `✓ 复盘完成（证据得分 ${result.assessment.evidenceScore}，等级未变）`;

      setState({ kind: "success", message });
      // 触发 Server Component 重新获取数据，技能雷达图实时更新
      router.refresh();
    } catch (err) {
      const message =
        err instanceof ApiError ? err.message : "复盘提交失败，请检查后端服务";
      setState({ kind: "error", message });
    }
  }

  const isSubmitting = state.kind === "submitting";

  return (
    <form
      onSubmit={handleSubmit}
      className="mt-2 space-y-3 rounded-lg bg-zinc-50 p-3 dark:bg-zinc-900"
    >
      {/* 学习日志 */}
      <div>
        <label className="text-xs font-medium text-zinc-600 dark:text-zinc-400">
          学习日志 <span className="text-red-500">*</span>
        </label>
        <textarea
          value={content}
          onChange={(e) => setContent(e.target.value)}
          rows={3}
          disabled={isSubmitting}
          placeholder="记录学到了什么、解决了什么问题、反思与改进点…（含 总结/反思/学到 等关键词可加分）"
          className="mt-1 w-full resize-none rounded-md border border-zinc-200 bg-white px-2 py-1.5 text-sm text-black placeholder:text-zinc-400 focus:border-black focus:outline-none dark:border-zinc-700 dark:bg-zinc-950 dark:text-zinc-50 dark:focus:border-zinc-300"
        />
        <p className="mt-0.5 text-[10px] text-zinc-400">
          {content.length} / 2000 字（≥20 字得分）
        </p>
      </div>

      {/* Artifact 链接 */}
      <div>
        <label className="text-xs font-medium text-zinc-600 dark:text-zinc-400">
          Artifact 链接（GitHub / 视频 / 代码，可选）
        </label>
        <input
          type="url"
          value={artifactUrl}
          onChange={(e) => setArtifactUrl(e.target.value)}
          disabled={isSubmitting}
          placeholder="https://github.com/yourname/your-repo"
          className="mt-1 w-full rounded-md border border-zinc-200 bg-white px-2 py-1.5 text-sm text-black placeholder:text-zinc-400 focus:border-black focus:outline-none dark:border-zinc-700 dark:bg-zinc-950 dark:text-zinc-50 dark:focus:border-zinc-300"
        />
      </div>

      {/* 实际耗时 */}
      <div>
        <label className="text-xs font-medium text-zinc-600 dark:text-zinc-400">
          实际耗时（分钟）
        </label>
        <input
          type="number"
          min={1}
          max={480}
          value={duration}
          onChange={(e) => setDuration(e.target.value)}
          disabled={isSubmitting}
          className="mt-1 w-24 rounded-md border border-zinc-200 bg-white px-2 py-1.5 text-sm text-black focus:border-black focus:outline-none dark:border-zinc-700 dark:bg-zinc-950 dark:text-zinc-50 dark:focus:border-zinc-300"
        />
      </div>

      {/* 操作按钮 */}
      <div className="flex items-center gap-2">
        <button
          type="submit"
          disabled={isSubmitting}
          className="rounded-md bg-black px-3 py-1.5 text-xs font-medium text-white transition hover:bg-zinc-800 disabled:opacity-50 dark:bg-white dark:text-black dark:hover:bg-zinc-200"
        >
          {isSubmitting ? "提交中…" : "提交复盘"}
        </button>
        <button
          type="button"
          onClick={onCancel}
          disabled={isSubmitting}
          className="rounded-md px-3 py-1.5 text-xs text-zinc-500 transition hover:text-zinc-700 disabled:opacity-50 dark:hover:text-zinc-300"
        >
          取消
        </button>
      </div>

      {/* 状态提示 */}
      {state.kind === "success" && (
        <p className="text-xs text-emerald-600 dark:text-emerald-400">
          {state.message}
        </p>
      )}
      {state.kind === "error" && (
        <p className="text-xs text-red-600 dark:text-red-400">{state.message}</p>
      )}
    </form>
  );
}
