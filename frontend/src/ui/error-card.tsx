import type { ReactNode } from "react";
import { ApiError } from "@/lib/apiClient";

type Props = {
  /** 页面名称（如"求职看板"），用于标题。 */
  pageName: string;
  /** 捕获到的错误。 */
  error: unknown;
};

/** 统一的页面级错误展示卡片。
 *
 * 所有页面共用，保证：
 *   - 错误标题格式一致
 *   - 恢复提示一致
 *   - 样式一致
 */
export default function ErrorCard({ pageName, error }: Props) {
  const message =
    error instanceof ApiError
      ? error.message
      : "无法连接后端服务，请确认 FastAPI 已启动";

  return (
    <main
      className="flex flex-1 items-center justify-center"
      style={{ background: "var(--surface-canvas)" }}
    >
      <div
        className="max-w-md text-center"
        style={{
          padding: 32,
          background: "var(--surface-card)",
          border: "1px solid var(--accent-danger)",
          borderRadius: "var(--radius-lg)",
        }}
      >
        <h1
          className="text-lg font-semibold"
          style={{ color: "var(--accent-danger)" }}
        >
          {pageName}加载失败
        </h1>
        <p className="mt-2 text-sm" style={{ color: "var(--text-muted)" }}>
          {message}
        </p>
        <p className="mt-4 text-xs" style={{ color: "var(--text-muted)" }}>
          请确认后端已启动：uvicorn app.main:app --reload --port 8000
        </p>
      </div>
    </main>
  );
}
