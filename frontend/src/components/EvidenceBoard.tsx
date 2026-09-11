"use client";

import { useState, type CSSProperties } from "react";
import type { SkillEvidence, SkillEvidenceItem } from "@/types";

type Props = {
  skills: SkillEvidence[];
};

// L0..L4 颜色（与证据强度对应）
const LEVEL_COLOR = ["#86868B", "#0EA5E9", "#8B5CF6", "#F59E0B", "#10B981"];

const KIND_PREFIX: Record<string, string> = {
  note: "因为这份笔记",
  question: "因为这道验证题",
  code: "因为这份代码",
  experiment: "因为这条实验",
  research: "因为这份对比实验 + 复现报告",
};

const cardStyle: CSSProperties = {
  background: "var(--color-card)",
  border: "1px solid var(--color-hairline)",
  borderRadius: "var(--radius-card-lg)",
  padding: "var(--spacing-lg)",
};

/** 技能证据链视图（P2 · 决策 3）：技能等级从自评变成「因为这份代码 / 实验」推导。
 *
 * 每条 typed evidence 的 ref 即「技能升级弹窗显示因为这份代码」的文案来源。
 */
export default function EvidenceBoard({ skills }: Props) {
  const [open, setOpen] = useState<string | null>(null);

  if (skills.length === 0) {
    return (
      <div style={cardStyle}>
        <span className="text-sm" style={{ color: "var(--color-ink-48)" }}>
          暂无技能数据。
        </span>
      </div>
    );
  }

  return (
    <div className="flex flex-col" style={{ gap: 14 }}>
      {skills.map((s) => {
        const isOpen = open === s.id;
        const gated = s.evidenceGate;
        return (
          <div key={s.id} style={cardStyle}>
            <button
              onClick={() => setOpen(isOpen ? null : s.id)}
              className="flex w-full items-center justify-between border-none"
              style={{
                background: "transparent",
                cursor: "pointer",
                padding: 0,
                gap: 12,
                textAlign: "left",
              }}
            >
              <div className="flex items-center" style={{ gap: 12, flexWrap: "wrap" }}>
                <span className="text-[15px] font-semibold" style={{ color: "var(--color-ink)" }}>
                  {s.name}
                </span>
                <span className="text-xs" style={{ color: "var(--color-ink-48)" }}>
                  自评 L{s.level} / 目标 L{s.targetLevel}
                </span>
              </div>
              <div className="flex items-center" style={{ gap: 12 }}>
                <GateBadge level={gated} />
                <span className="text-xs" style={{ color: "var(--color-ink-48)" }}>
                  {s.evidence.length} 条证据 {isOpen ? "▲" : "▼"}
                </span>
              </div>
            </button>

            {isOpen && (
              <div className="flex flex-col" style={{ gap: 10, marginTop: 14 }}>
                {s.evidence.length === 0 ? (
                  <span className="text-xs" style={{ color: "var(--color-ink-48)", lineHeight: 1.7 }}>
                    暂无证据 —— 该技能等级仍靠自评。把对应课程日的代码 / 笔记 / commit 或一条
                    Experiment 录进来，证据链会自动推导可信等级。
                  </span>
                ) : (
                  s.evidence
                    .slice()
                    .sort((a, b) => a.level - b.level)
                    .map((e: SkillEvidenceItem, i) => (
                      <div
                        key={i}
                        className="flex items-start"
                        style={{
                          gap: 10,
                          padding: "10px 12px",
                          background: "#FAFAFB",
                          borderRadius: "var(--radius-item-md)",
                        }}
                      >
                        <span
                          className="inline-flex items-center justify-center shrink-0"
                          style={{
                            minWidth: 22,
                            height: 22,
                            padding: "0 6px",
                            borderRadius: "var(--radius-pill)",
                            fontSize: 11,
                            fontWeight: 700,
                            color: "#fff",
                            background: LEVEL_COLOR[e.level] ?? "#86868B",
                          }}
                        >
                          L{e.level}
                        </span>
                        <div className="flex flex-col" style={{ gap: 2, minWidth: 0 }}>
                          <span className="text-[13px] font-medium" style={{ color: "var(--color-ink)" }}>
                            {e.label}
                          </span>
                          <span className="text-xs" style={{ color: "var(--color-ink-48)", lineHeight: 1.6 }}>
                            {KIND_PREFIX[e.kind] ?? "因为"}：{e.ref}
                          </span>
                        </div>
                      </div>
                    ))
                )}
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}

function GateBadge({ level }: { level: number }) {
  const color = LEVEL_COLOR[level] ?? "#86868B";
  return (
    <span
      className="inline-flex items-center"
      style={{
        padding: "3px 10px",
        borderRadius: "var(--radius-pill)",
        fontSize: 11,
        fontWeight: 700,
        color: "#fff",
        background: color,
      }}
    >
      证据可信 L{level}
    </span>
  );
}
