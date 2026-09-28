"use client";

/** 今日复盘板：提交一条学习日志 + 今日已记列表。
 * 记录的是「实质」不是「勾选」——content 必填即产品约束（spec §3.2）。 */

import { useEffect, useState } from "react";
import { ApiError } from "@/lib/apiClient";
import { createLearningLog, isToday, listLearningLogs } from "@/services/learningLogService";
import type { LearningLog } from "@/types";

export default function ReviewBoard() {
  const [logs, setLogs] = useState<LearningLog[]>([]);
  const [content, setContent] = useState("");
  const [minutes, setMinutes] = useState("");
  const [url, setUrl] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // 数据拉取走 promise 回调（react-hooks/set-state-in-effect：effect 内不得同步 setState）
  function refresh(): Promise<void> {
    return listLearningLogs()
      .then((items) => setLogs(items.filter((l) => isToday(l))))
      .catch(() => setLogs([]));
  }

  useEffect(() => {
    void refresh();
  }, []);

  async function submit() {
    if (!content.trim()) {
      setError("content 必填：写清今天到底做了什么");
      return;
    }
    setBusy(true);
    setError(null);
    try {
      await createLearningLog({
        content: content.trim(),
        durationMinutes: minutes ? Number(minutes) : null,
        artifactUrl: url.trim() || null,
      });
      setContent("");
      setMinutes("");
      setUrl("");
      await refresh();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "提交失败，请检查后端服务");
    } finally {
      setBusy(false);
    }
  }

  return (
    <section
      className="flex flex-col"
      style={{ gap: 16, padding: 24, background: "var(--surface-card)", borderRadius: "var(--radius-lg)" }}
    >
      <h2 className="text-base font-semibold">今天学到什么</h2>
      <textarea
        value={content}
        onChange={(e) => setContent(e.target.value)}
        placeholder="例：把 DPO 的 loss 推导过了一遍，弄清了 reference model 的作用——卡点在式 (4) 的隐式奖励。"
        rows={4}
        style={{ width: "100%", padding: 12, borderRadius: "var(--radius-md)", border: "1px solid var(--border-default)" }}
      />
      <div className="flex flex-wrap items-center" style={{ gap: 12 }}>
        <input
          type="number"
          min={1}
          max={480}
          value={minutes}
          onChange={(e) => setMinutes(e.target.value)}
          placeholder="时长（分钟）"
          style={{ width: 140, padding: 8, borderRadius: "var(--radius-md)", border: "1px solid var(--border-default)" }}
        />
        <input
          value={url}
          onChange={(e) => setUrl(e.target.value)}
          placeholder="证据链接（GitHub / 文档 / 笔记，可空）"
          style={{ flex: 1, minWidth: 240, padding: 8, borderRadius: "var(--radius-md)", border: "1px solid var(--border-default)" }}
        />
        <button
          type="button"
          onClick={submit}
          disabled={busy}
          style={{
            padding: "8px 20px",
            borderRadius: "var(--radius-pill)",
            background: "var(--accent-primary)",
            color: "var(--text-inverse)",
            border: "none",
            cursor: busy ? "not-allowed" : "pointer",
            opacity: busy ? 0.7 : 1,
          }}
        >
          {busy ? "提交中..." : "记一笔"}
        </button>
      </div>
      {error ? (
        <p className="text-xs" style={{ color: "var(--accent-danger)" }}>
          ✗ {error}
        </p>
      ) : null}

      <h3 className="text-sm font-semibold" style={{ color: "var(--text-muted)" }}>
        今日已记 {logs.length} 条
      </h3>
      {logs.length === 0 ? (
        <p className="text-xs" style={{ color: "var(--text-muted)" }}>
          今天还没有实质记录——学完 10 分钟就来写一句，比勾选有用。
        </p>
      ) : (
        <ul className="flex flex-col" style={{ gap: 8, listStyle: "none", padding: 0 }}>
          {logs.map((l) => (
            <li
              key={l.id}
              style={{ padding: 12, border: "1px solid var(--border-default)", borderRadius: "var(--radius-md)" }}
            >
              <p className="text-sm">{l.content}</p>
              <p className="text-xs" style={{ color: "var(--text-muted)" }}>
                {l.durationMinutes ? `${l.durationMinutes} 分钟 · ` : ""}
                {l.artifactUrl ? (
                  <a href={l.artifactUrl} target="_blank" rel="noopener noreferrer">
                    证据
                  </a>
                ) : (
                  "无证据链接"
                )}
              </p>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
