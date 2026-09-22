"use client";

/** 项目 README 骨架卡（P4）。
 *
 * 把「证据链 → 论文体 README」这条链路做成可操作的：预览 / 重新生成 / 保存到项目 /
 * 复制 / 下载 .md。目标是 Day 24 验收的「导出 + 润色」，而不是「从空白开始写」。
 *
 * 数据：初值由 Server Component 传入（getProjectReadme），后续操作走 packagingService。
 */

import { useState } from "react";
import type { ProjectReadme } from "@/types";
import { getProjectReadme, saveProjectReadme } from "@/services/packagingService";

type Props = {
  projectId: string;
  initial: ProjectReadme;
};

export default function ReadmeDraftCard({ projectId, initial }: Props) {
  const [draft, setDraft] = useState(initial.draft);
  const [saved, setSaved] = useState<string | null>(initial.savedReadme);
  const [counts, setCounts] = useState(initial.counts);
  const [busy, setBusy] = useState<"regen" | "save" | null>(null);
  const [msg, setMsg] = useState<string | null>(null);

  const dirty = saved !== null && saved !== draft;

  async function handleRegen() {
    setBusy("regen");
    setMsg(null);
    try {
      const r = await getProjectReadme(projectId);
      setDraft(r.draft);
      setSaved(r.savedReadme);
      setCounts(r.counts);
      setMsg("已按最新证据链重新生成");
    } catch {
      setMsg("重新生成失败：后端未响应");
    } finally {
      setBusy(null);
    }
  }

  async function handleSave() {
    setBusy("save");
    setMsg(null);
    try {
      const r = await saveProjectReadme(projectId, draft);
      setSaved(r.savedReadme);
      setCounts({ ...counts, chars: r.chars });
      setMsg(`已保存到项目（${r.chars} 字符）`);
    } catch {
      setMsg("保存失败：后端未响应");
    } finally {
      setBusy(null);
    }
  }

  async function handleCopy() {
    try {
      await navigator.clipboard.writeText(draft);
      setMsg("已复制到剪贴板");
    } catch {
      setMsg("复制失败：浏览器未授权剪贴板");
    }
  }

  function handleDownload() {
    const blob = new Blob([draft], { type: "text/markdown;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "README.md";
    a.click();
    URL.revokeObjectURL(url);
  }

  return (
    <section
      className="flex flex-col"
      style={{
        gap: 16,
        padding: "var(--spacing-lg)",
        background: "var(--color-card)",
        border: "1px solid var(--color-hairline)",
        borderRadius: "var(--radius-card-lg)",
      }}
    >
      <div className="flex items-center justify-between" style={{ gap: 12 }}>
        <div className="flex flex-col" style={{ gap: 4 }}>
          <span
            className="text-[17px] font-semibold"
            style={{ color: "var(--color-ink)" }}
          >
            README 骨架（从证据链生成）
          </span>
          <span className="text-xs" style={{ color: "var(--color-ink-48)" }}>
            里程碑 {counts.milestones} · 技能 {counts.skills}（有证据{" "}
            {counts.skillsWithEvidence}） · 实验 {counts.experiments} · {counts.chars} 字符
          </span>
        </div>
        {saved === null ? (
          <Badge label="尚未保存" bg="#F5F5F5" color="var(--color-ink-48)" />
        ) : dirty ? (
          <Badge
            label="草稿已改动"
            bg="var(--color-amber-soft)"
            color="var(--color-amber-deep)"
          />
        ) : (
          <Badge
            label="与已保存一致"
            bg="var(--color-emerald-soft)"
            color="var(--color-emerald-deep)"
          />
        )}
      </div>

      <div className="flex flex-wrap" style={{ gap: 8 }}>
        <Action label={busy === "regen" ? "生成中…" : "重新生成"} onClick={handleRegen} disabled={busy !== null} />
        <Action
          label={busy === "save" ? "保存中…" : "保存到项目"}
          onClick={handleSave}
          disabled={busy !== null}
          primary
        />
        <Action label="复制" onClick={handleCopy} disabled={busy !== null} />
        <Action label="下载 .md" onClick={handleDownload} disabled={busy !== null} />
      </div>

      {msg && (
        <span className="text-xs" style={{ color: "var(--color-ink-48)" }}>
          {msg}
        </span>
      )}

      <pre
        className="overflow-auto"
        style={{
          margin: 0,
          maxHeight: 460,
          padding: "14px 16px",
          background: "var(--color-item-bg)",
          border: "1px solid var(--color-hairline-soft)",
          borderRadius: "var(--radius-item-md)",
          fontSize: 12,
          lineHeight: 1.65,
          color: "var(--color-ink-80)",
          whiteSpace: "pre-wrap",
          wordBreak: "break-word",
          fontFamily:
            "ui-monospace, SFMono-Regular, Menlo, Consolas, monospace",
        }}
      >
        {draft}
      </pre>

      <p className="text-xs" style={{ color: "var(--color-ink-48)" }}>
        带 📝 的段落需要你补写，其余已由证据链自动填好 —— 导出后在本地润色，不要从空白开始。
      </p>
    </section>
  );
}

function Badge({ label, bg, color }: { label: string; bg: string; color: string }) {
  return (
    <span
      className="inline-flex shrink-0 items-center"
      style={{
        padding: "4px 10px",
        borderRadius: "var(--radius-pill)",
        fontSize: 11,
        fontWeight: 600,
        background: bg,
        color,
      }}
    >
      {label}
    </span>
  );
}

function Action({
  label,
  onClick,
  disabled,
  primary,
}: {
  label: string;
  onClick: () => void;
  disabled?: boolean;
  primary?: boolean;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled}
      style={{
        padding: "7px 14px",
        borderRadius: "var(--radius-item-sm)",
        border: primary ? "1px solid transparent" : "1px solid var(--color-hairline)",
        background: primary ? "var(--color-ink)" : "var(--color-card)",
        color: primary ? "var(--color-on-primary)" : "var(--color-ink-80)",
        fontSize: 12,
        fontWeight: 600,
        cursor: disabled ? "not-allowed" : "pointer",
        opacity: disabled ? 0.55 : 1,
      }}
    >
      {label}
    </button>
  );
}
