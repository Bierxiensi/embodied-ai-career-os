"use client";

/** 掌握单元视图：摘要/概念卡 → 测验实证 → Teach-Back 口述回收。
 * 完成判据三选一（spec §3.2）：测验过 / Teach-Back 过 / 证据挂上。 */

import { useState } from "react";
import { answerItem, teachBackComplete } from "@/services/masteryService";
import type { MasteryUnit, UnitItem } from "@/types";

const KIND_LABEL: Record<UnitItem["kind"], string> = {
  summary: "摘要",
  concept_card: "概念卡",
  quiz_q: "测验",
  exercise: "思考题",
  flashcard: "复习卡",
};

export default function UnitView({ unit }: { unit: MasteryUnit }) {
  const [answers, setAnswers] = useState<Record<number, string>>({});
  const [verdicts, setVerdicts] = useState<Record<number, { correct: boolean; rationale: string | null; judgeMode: "llm" | "rule" }>>({});
  const [tbResult, setTbResult] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function submitAnswer(item: UnitItem) {
    const text = (answers[item.id] ?? "").trim();
    if (!text) return;
    setBusy(true);
    try {
      const r = await answerItem(unit.id, item.id, text);
      setVerdicts((v) => ({ ...v, [item.id]: { correct: r.correct, rationale: r.rationale, judgeMode: r.judgeMode } }));
    } finally {
      setBusy(false);
    }
  }

  async function submitTeachBack() {
    const quiz = unit.items.filter((i) => i.kind === "quiz_q");
    const spoken = quiz
      .map((i) => ({ itemId: i.id, spoken: (answers[i.id] ?? "").trim() }))
      .filter((a) => a.spoken);
    if (spoken.length === 0) return;
    setBusy(true);
    try {
      const r = await teachBackComplete({ unitId: unit.id, answers: spoken });
      const passed = r.verdicts.filter((v) => v.passed).length;
      const ruleNote = r.verdicts.some((v) => v.judgeMode === "rule") ? "（含规则判分）" : "";
      setTbResult(`Teach-Back 完成：${passed}/${r.verdicts.length} 通过，已自动写入学习日志（错项 ${r.cardsCreated} 张进复习队列）${ruleNote}。`);
    } finally {
      setBusy(false);
    }
  }

  return (
    <section
      className="flex flex-col"
      style={{ gap: 16, padding: 24, background: "var(--surface-card)", borderRadius: "var(--radius-lg)" }}
    >
      <div className="flex items-center" style={{ gap: 8 }}>
        <h2 className="text-base font-semibold">{unit.title}</h2>
        <span
          className="text-xs"
          style={{
            padding: "2px 8px",
            borderRadius: "var(--radius-pill)",
            background: unit.generationMode === "llm" ? "var(--accent-primary-soft, #DBEAFE)" : "var(--surface-muted, #F4F4F5)",
            color: unit.generationMode === "llm" ? "var(--accent-primary)" : "var(--text-muted)",
          }}
        >
          {unit.generationMode === "llm" ? "AI 生成" : "规则兜底（LLM 不可用）"}
        </span>
      </div>

      {unit.items.map((item) => (
        <div
          key={item.id}
          style={{ padding: 12, border: "1px solid var(--border-default)", borderRadius: "var(--radius-md)" }}
        >
          <p className="text-xs font-semibold" style={{ color: "var(--text-muted)" }}>
            {KIND_LABEL[item.kind]}
            {item.isVerified ? " · 已实证 ✓" : ""}
          </p>
          <p className="text-sm" style={{ whiteSpace: "pre-wrap" }}>{item.body}</p>

          {item.kind === "quiz_q" ? (
            <div className="mt-2 flex flex-wrap items-center" style={{ gap: 8 }}>
              <input
                value={answers[item.id] ?? ""}
                onChange={(e) => setAnswers((a) => ({ ...a, [item.id]: e.target.value }))}
                placeholder="闭卷作答（答对即实证）"
                style={{ flex: 1, minWidth: 200, padding: 8, borderRadius: "var(--radius-md)", border: "1px solid var(--border-default)" }}
              />
              <button
                type="button"
                disabled={busy}
                onClick={() => submitAnswer(item)}
                style={{ padding: "6px 16px", borderRadius: "var(--radius-pill)", background: "var(--accent-primary)", color: "var(--text-inverse)", border: "none", cursor: "pointer" }}
              >
                提交
              </button>
              {verdicts[item.id] ? (
                <span className="text-xs" style={{ color: verdicts[item.id].correct ? "var(--accent-success, #16A34A)" : "var(--accent-danger)" }}>
                  {/* 降级可见：规则判分时在徽章上如实标注（与 AI 生成徽章同款纪律） */}
                  {verdicts[item.id].correct ? "✓ 通过" : `✗ ${verdicts[item.id].rationale ?? "再试一次"}`}
                  {verdicts[item.id].judgeMode === "rule" ? " · 规则判分" : ""}
                </span>
              ) : null}
            </div>
          ) : null}
        </div>
      ))}

      <div className="flex items-center" style={{ gap: 12 }}>
        <button
          type="button"
          disabled={busy}
          onClick={submitTeachBack}
          style={{ padding: "8px 20px", borderRadius: "var(--radius-pill)", background: "var(--accent-primary)", color: "var(--text-inverse)", border: "none", cursor: busy ? "not-allowed" : "pointer", opacity: busy ? 0.7 : 1 }}
        >
          Teach-Back：口述回收
        </button>
        {tbResult ? <p className="text-xs" style={{ color: "var(--text-muted)" }}>{tbResult}</p> : null}
      </div>
    </section>
  );
}
