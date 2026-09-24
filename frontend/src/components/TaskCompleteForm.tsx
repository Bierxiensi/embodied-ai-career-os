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

  /** 输入框统一样式 —— 用设计 token，替代原先的 zinc/dark: Tailwind 直出配色
   *  （token 自带暗色值，再叠 `dark:` 会互相打架，且与卡片其余部分不一致）。 */
  const fieldStyle: React.CSSProperties = {
    width: "100%",
    marginTop: 4,
    padding: "7px 10px",
    fontSize: 13,
    color: "var(--text-primary)",
    background: "var(--surface-card)",
    border: "1px solid var(--border-default)",
    borderRadius: "var(--radius-sm)",
    outline: "none",
    resize: "none",
  };

  const labelStyle: React.CSSProperties = {
    fontSize: 12,
    fontWeight: 500,
    color: "var(--text-muted)",
  };

  return (
    <form
      onSubmit={handleSubmit}
      className="flex flex-col"
      style={{
        gap: 12,
        marginTop: 8,
        padding: 14,
        background: "var(--surface-card)",
        border: "1px solid var(--border-default)",
        borderRadius: "var(--radius-md)",
      }}
    >
      {/* 学习日志 */}
      <div className="flex flex-col">
        <label style={labelStyle}>
          学习日志 <span style={{ color: "var(--accent-danger)" }}>*</span>
        </label>
        <textarea
          value={content}
          onChange={(e) => setContent(e.target.value)}
          rows={3}
          disabled={isSubmitting}
          placeholder="记录学到了什么、解决了什么问题、反思与改进点…（含 总结/反思/学到 等关键词可加分）"
          style={fieldStyle}
        />
        <span
          style={{ marginTop: 4, fontSize: 10, color: "var(--text-muted)" }}
        >
          {content.length} / 2000 字（≥20 字得分）
        </span>
      </div>

      {/* Artifact 链接 */}
      <div className="flex flex-col">
        <label style={labelStyle}>
          Artifact 链接（GitHub / 视频 / 代码，可选）
        </label>
        <input
          type="url"
          value={artifactUrl}
          onChange={(e) => setArtifactUrl(e.target.value)}
          disabled={isSubmitting}
          placeholder="https://github.com/yourname/your-repo"
          style={fieldStyle}
        />
      </div>

      {/* 实际耗时 */}
      <div className="flex flex-col">
        <label style={labelStyle}>实际耗时（分钟）</label>
        <input
          type="number"
          min={1}
          max={480}
          value={duration}
          onChange={(e) => setDuration(e.target.value)}
          disabled={isSubmitting}
          style={{ ...fieldStyle, width: 96 }}
        />
      </div>

      {/* 操作按钮 */}
      <div className="flex items-center" style={{ gap: 8 }}>
        <button
          type="submit"
          disabled={isSubmitting}
          className="border-none"
          style={{
            padding: "7px 14px",
            fontSize: 12,
            fontWeight: 600,
            background: "var(--accent-primary)",
            color: "var(--text-inverse)",
            borderRadius: "var(--radius-pill)",
            border: "none",
            cursor: isSubmitting ? "not-allowed" : "pointer",
            opacity: isSubmitting ? 0.6 : 1,
          }}
        >
          {isSubmitting ? "提交中…" : "提交复盘"}
        </button>
        <button
          type="button"
          onClick={onCancel}
          disabled={isSubmitting}
          className="border-none"
          style={{
            padding: "7px 14px",
            fontSize: 12,
            background: "transparent",
            color: "var(--text-muted)",
            border: "none",
            cursor: isSubmitting ? "not-allowed" : "pointer",
            opacity: isSubmitting ? 0.6 : 1,
          }}
        >
          取消
        </button>
      </div>

      {/* 状态提示 */}
      {state.kind === "success" && (
        <p style={{ fontSize: 12, color: "var(--accent-success)" }}>
          {state.message}
        </p>
      )}
      {state.kind === "error" && (
        <p style={{ fontSize: 12, color: "var(--accent-danger)" }}>
          {state.message}
        </p>
      )}
    </form>
  );
}
