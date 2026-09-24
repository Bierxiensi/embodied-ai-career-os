"use client";

/** 简历技能行（附证据）（P4 · plan_30d Day 25）。
 *
 * 验收标准：「简历技能行每一项都能点开对应证据（代码 / 实验 / 论文）」。
 *
 * - ready   ：有真实证据（L1 起）的技能，可直接写进简历，每行展开即证据
 * - pending ：自评较强却尚无证据的技能 —— 写进简历即虚构风险，先去补证据
 */

import { useState } from "react";
import type { SkillLineReport, SkillEvidenceItem } from "@/types";

type Props = {
  report: SkillLineReport;
};

const LEVEL_LABEL: Record<number, string> = {
  1: "能解释",
  2: "能实现/修改",
  3: "能做实验",
  4: "能研究",
};

export default function SkillLinesCard({ report }: Props) {
  const [msg, setMsg] = useState<string | null>(null);

  async function copyAll() {
    const text = report.ready.map((r) => `- ${r.line}`).join("\n");
    try {
      await navigator.clipboard.writeText(text);
      setMsg(`已复制 ${report.ready.length} 行`);
    } catch {
      setMsg("复制失败：浏览器未授权剪贴板");
    }
  }

  const { ready, pending, summary, note } = report;

  return (
    <section
      className="flex flex-col"
      style={{
        gap: 16,
        padding: 24,
        background: "var(--surface-card)",
        border: "1px solid var(--border-default)",
        borderRadius: "var(--radius-lg)",
      }}
    >
      <div className="flex items-center justify-between" style={{ gap: 12 }}>
        <div className="flex flex-col" style={{ gap: 4 }}>
          <span className="text-[15px] font-semibold" style={{ color: "var(--text-primary)" }}>
            技能行（附证据）
          </span>
          <span className="text-xs" style={{ color: "var(--text-muted)" }}>
            可写进简历 {summary.ready} 项 · 待补证据 {summary.pending} 项 · 技能总数{" "}
            {summary.total}
          </span>
        </div>
        {summary.ready > 0 && (
          <button
            type="button"
            onClick={copyAll}
            style={{
              padding: "7px 14px",
              borderRadius: "var(--radius-sm)",
              border: "1px solid var(--border-default)",
              background: "var(--surface-card)",
              color: "var(--text-secondary)",
              fontSize: 12,
              fontWeight: 600,
              cursor: "pointer",
            }}
          >
            复制全部
          </button>
        )}
      </div>

      {msg && (
        <span className="text-xs" style={{ color: "var(--text-muted)" }}>
          {msg}
        </span>
      )}

      {/* ready */}
      {ready.length > 0 ? (
        <div className="flex flex-col" style={{ gap: 10 }}>
          {ready.map((r) => (
            <div
              key={r.skill}
              className="flex flex-col"
              style={{
                gap: 8,
                padding: "12px 14px",
                background: "var(--color-item-bg)",
                borderRadius: "var(--radius-md)",
              }}
            >
              <div className="flex items-center" style={{ gap: 8 }}>
                <span className="text-sm font-medium" style={{ color: "var(--text-primary)" }}>
                  {r.skill}
                </span>
                <span
                  className="inline-flex shrink-0 items-center"
                  style={{
                    padding: "2px 8px",
                    borderRadius: "var(--radius-pill)",
                    fontSize: 10,
                    fontWeight: 700,
                    background: "var(--accent-success-soft)",
                    color: "var(--accent-success)",
                  }}
                >
                  L{r.gateLevel}
                </span>
                <span className="ml-auto text-xs" style={{ color: "var(--text-muted)" }}>
                  自评 L{r.level}
                </span>
              </div>
              <div className="flex flex-col" style={{ gap: 4 }}>
                {r.refs.map((ref, i) => (
                  <RefLine key={i} item={ref} />
                ))}
              </div>
            </div>
          ))}
        </div>
      ) : (
        <div
          style={{
            padding: "14px 16px",
            background: "var(--color-item-bg)",
            borderRadius: "var(--radius-md)",
            fontSize: 12,
            color: "var(--text-muted)",
            lineHeight: 1.7,
          }}
        >
          尚无技能拿到 L1 证据 —— 还没有可以写进简历的技能行。
          <br />
          解锁方式（任一）：到「今日」完成某课程日的**笔记**，或录一道带 `skill_name` 的**面试题**；
          之后有代码 + commit 升 L2，有实验升 L3，有对比实验 + 复现报告升 L4。
        </div>
      )}

      {/* pending */}
      {pending.length > 0 && (
        <div className="flex flex-col" style={{ gap: 8 }}>
          <span className="text-xs font-semibold" style={{ color: "var(--accent-warning)" }}>
            ⚠️ 待补证据（自评 L{summary.pendingMinLevel}+ 但无证据 —— 现在写进简历即虚构）
          </span>
          <div className="flex flex-wrap" style={{ gap: 6 }}>
            {pending.map((p) => (
              <span
                key={p.skill}
                title={p.missing}
                className="inline-flex items-center"
                style={{
                  padding: "3px 9px",
                  borderRadius: "var(--radius-pill)",
                  fontSize: 11,
                  fontWeight: 600,
                  background: "var(--accent-warning-soft)",
                  color: "var(--accent-warning)",
                }}
              >
                {p.skill} · L{p.level}
              </span>
            ))}
          </div>
        </div>
      )}

      {note && (
        <p className="text-xs" style={{ color: "var(--text-muted)", lineHeight: 1.7 }}>
          {note}
        </p>
      )}
    </section>
  );
}

function RefLine({ item }: { item: SkillEvidenceItem }) {
  const isUrl = /^https?:\/\//.test(item.ref);
  return (
    <span className="text-xs" style={{ color: "var(--text-muted)", lineHeight: 1.7 }}>
      <span
        style={{
          fontWeight: 700,
          color: "var(--accent-success)",
          marginRight: 6,
        }}
      >
        L{item.level} {LEVEL_LABEL[item.level] ?? item.label}
      </span>
      {isUrl ? (
        <a
          href={item.ref}
          target="_blank"
          rel="noreferrer"
          style={{ color: "var(--accent-primary)" }}
        >
          {item.ref}
        </a>
      ) : (
        item.ref
      )}
    </span>
  );
}
