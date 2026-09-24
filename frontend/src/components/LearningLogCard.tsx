"use client";

import { useState, type CSSProperties } from "react";
import { useRouter } from "next/navigation";

import { createLearningLog, isToday } from "@/services/learningLogService";
import type { LearningLog } from "@/types";

/** 「今天学到什么」—— 今日施工单的**内容位**。
 *
 * 为什么需要它：四件套（代码/笔记/面试题/commit）是**布尔勾选 + 自动标题**，
 * 点一下只留下一条 `title="Day N · 代码"`，写不了"我今天具体做了什么、卡在哪、产出在哪"。
 * 实测 `day_artifacts` 至今 0 行 —— 施工单从一开始就是"记状态"，不是"记实质"。
 * 学习日志（learning_logs）补的就是这个位：content 必填、含反思、可挂证据链接，
 * 且它是 Reviewer Agent 的输入、是 Portfolio 的证据来源。
 *
 * 数据流：logs 由 today/page.tsx（Server Component）取好下发；
 * 提交后 router.refresh() 重新取数 —— 与四件套勾选同一套模式，不用客户端 useEffect。
 *
 * 注意：后端**不提供删除**（历史日志是 Reviewer 的决策依据，同 Task 的设计）。
 */

const cardStyle: CSSProperties = {
  background: "var(--color-card)",
  border: "1px solid var(--color-hairline)",
  borderRadius: "var(--radius-card-lg)",
  padding: "var(--spacing-lg)",
};

const INPUT: CSSProperties = {
  padding: "8px 11px",
  borderRadius: "var(--radius-item-md)",
  border: "1px solid var(--color-hairline)",
  background: "var(--color-item-bg)",
  color: "var(--color-ink)",
  fontSize: 13,
  fontFamily: "inherit",
};

const MAX_CONTENT = 2000;

export default function LearningLogCard({ logs }: { logs: LearningLog[] }) {
  const router = useRouter();
  const [content, setContent] = useState("");
  const [minutes, setMinutes] = useState("");
  const [url, setUrl] = useState("");
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const todays = logs.filter((l) => isToday(l));
  const totalMinutes = todays.reduce((sum, l) => sum + (l.durationMinutes ?? 0), 0);

  async function onSubmit() {
    const text = content.trim();
    if (!text || pending) return;

    // 与后端校验对齐（duration 1-480），提前拦一次给出人话提示
    let duration: number | null = null;
    if (minutes.trim()) {
      const n = Number(minutes);
      if (!Number.isFinite(n) || n < 1 || n > 480) {
        setError("时长需在 1-480 分钟之间（留空表示不计）");
        return;
      }
      duration = Math.round(n);
    }

    setPending(true);
    setError(null);
    try {
      await createLearningLog({
        content: text,
        durationMinutes: duration,
        artifactUrl: url.trim() || null,
      });
      setContent("");
      setMinutes("");
      setUrl("");
      router.refresh();
    } catch (e) {
      setError(e instanceof Error ? e.message : "保存失败");
    } finally {
      setPending(false);
    }
  }

  return (
    <div className="flex flex-col" style={{ ...cardStyle, gap: 14 }}>
      <div className="flex items-baseline justify-between" style={{ gap: 12 }}>
        <span className="text-[15px] font-semibold" style={{ color: "var(--color-ink)" }}>
          今天学到什么
        </span>
        <span className="text-xs" style={{ color: "var(--color-ink-48)" }}>
          {todays.length === 0
            ? "今天还没有记录"
            : `今天 ${todays.length} 条 · 累计 ${totalMinutes} 分钟`}
        </span>
      </div>

      <span className="text-[11px]" style={{ color: "var(--color-ink-48)", lineHeight: 1.6 }}>
        写具体做了什么、卡在哪、产出在哪。这条记录会进入 Reviewer 评审，也作为能力证据留档。
      </span>

      <textarea
        value={content}
        onChange={(e) => setContent(e.target.value.slice(0, MAX_CONTENT))}
        rows={3}
        placeholder="例：跑通 DPO 训练脚本，发现 loss 在 beta=0.1 时不收敛，查文档后改成 0.01 恢复正常。"
        style={{ ...INPUT, resize: "vertical", lineHeight: 1.65 }}
      />

      <div className="flex flex-wrap items-center" style={{ gap: 10 }}>
        <input
          value={minutes}
          onChange={(e) => setMinutes(e.target.value.replace(/[^\d]/g, ""))}
          inputMode="numeric"
          placeholder="时长（分钟，可空）"
          style={{ ...INPUT, width: 150 }}
        />
        <input
          value={url}
          onChange={(e) => setUrl(e.target.value.slice(0, 500))}
          placeholder="证据链接（GitHub / 博客 / 视频，可空）"
          style={{ ...INPUT, flex: "1 1 240px", minWidth: 200 }}
        />
        <button
          onClick={() => void onSubmit()}
          disabled={pending || !content.trim()}
          className="text-[13px] font-medium"
          style={{
            padding: "9px 18px",
            borderRadius: "var(--radius-item-md)",
            border: "none",
            background: "var(--color-primary)",
            color: "var(--color-on-primary)",
            cursor: pending ? "wait" : "pointer",
            opacity: pending || !content.trim() ? 0.6 : 1,
          }}
        >
          {pending ? "保存中…" : "记录"}
        </button>
        <span className="text-[11px]" style={{ color: "var(--color-ink-48)" }}>
          {content.length}/{MAX_CONTENT}
        </span>
      </div>

      {error && (
        <span className="text-xs" style={{ color: "var(--color-rose-deep)" }}>
          {error}
        </span>
      )}

      {todays.length > 0 && (
        <div className="flex flex-col" style={{ gap: 8 }}>
          {todays.map((l) => (
            <div
              key={l.id}
              className="flex flex-col"
              style={{
                gap: 5,
                padding: "10px 12px",
                borderRadius: "var(--radius-item-md)",
                background: "var(--color-item-bg)",
                border: "1px solid var(--color-hairline)",
              }}
            >
              <div className="flex flex-wrap items-center" style={{ gap: 8 }}>
                <span className="text-[11px]" style={{ color: "var(--color-ink-48)" }}>
                  {new Date(l.createdAt).toLocaleTimeString("zh-CN", {
                    hour: "2-digit",
                    minute: "2-digit",
                  })}
                </span>
                {l.durationMinutes !== null && (
                  <span
                    className="text-[11px] font-semibold"
                    style={{
                      padding: "2px 8px",
                      borderRadius: "var(--radius-pill)",
                      background: "var(--color-primary-soft)",
                      color: "var(--color-primary)",
                    }}
                  >
                    {l.durationMinutes} 分钟
                  </span>
                )}
                {l.artifactUrl && (
                  <a
                    href={l.artifactUrl}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-[11px] no-underline"
                    style={{ color: "var(--color-primary)" }}
                  >
                    证据 ↗
                  </a>
                )}
              </div>
              <span
                className="text-[13px]"
                style={{ color: "var(--color-ink-80)", lineHeight: 1.65, whiteSpace: "pre-wrap" }}
              >
                {l.content}
              </span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
