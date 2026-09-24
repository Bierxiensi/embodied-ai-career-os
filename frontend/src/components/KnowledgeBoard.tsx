"use client";

import { useState, type CSSProperties } from "react";

import { askKnowledge, searchKnowledge } from "@/services/knowledgeService";
import type { KnowledgeAnswer, KnowledgeCitation, KnowledgeStats } from "@/types";

/** 知识库页客户端交互层。
 *
 * 三个问题：
 *   1. 库里有什么        → 顶部统计（口径全部透传后端，前端不重算）
 *   2. 这个概念在哪      → 检索：query → 命中片段 + 相似度 + 出处
 *   3. 卡住了问一句      → 问答：question → 成句回答 + 引用
 *
 * 两个「降级可见」设计（本项目反复栽过的坑：降级了但看不出来）：
 *   · 嵌入模型为 hash-384 时显式告警 —— 那是伪嵌入，检索会"看起来能用但不准"
 *   · answerMode=rule 时标注"片段兜底" —— 说明 LLM 不可用，返回的是原文堆叠不是回答
 */

const cardStyle: CSSProperties = {
  background: "var(--surface-card)",
  border: "1px solid var(--border-default)",
  borderRadius: "var(--radius-lg)",
  padding: "var(--spacing-lg)",
};

/** 置信度三态配色。后端给的是 high/medium/low，未知值按 low 处理。 */
const CONFIDENCE_META: Record<string, { label: string; color: string; soft: string }> = {
  high: { label: "高", color: "var(--accent-success)", soft: "var(--accent-success-soft)" },
  medium: { label: "中", color: "var(--accent-warning)", soft: "var(--accent-warning-soft)" },
  low: { label: "低", color: "var(--accent-danger)", soft: "var(--accent-danger-soft)" },
};

const PILL: CSSProperties = {
  display: "inline-flex",
  alignItems: "center",
  padding: "2px 8px",
  borderRadius: "var(--radius-pill)",
  fontSize: 11,
  fontWeight: 600,
};

function Notice({ tone, children }: { tone: "amber" | "rose"; children: React.ReactNode }) {
  const meta =
    tone === "amber"
      ? { bg: "var(--accent-warning-soft)", fg: "var(--accent-warning)", bd: "var(--accent-warning)" }
      : { bg: "var(--accent-danger-soft)", fg: "var(--accent-danger)", bd: "var(--accent-danger)" };
  return (
    <div
      className="text-xs"
      style={{
        padding: "8px 12px",
        borderRadius: "var(--radius-md)",
        background: meta.bg,
        color: meta.fg,
        border: `1px solid ${meta.bd}`,
        lineHeight: 1.6,
      }}
    >
      {children}
    </div>
  );
}

function CitationList({ citations }: { citations: KnowledgeCitation[] }) {
  if (citations.length === 0) return null;
  return (
    <div className="flex flex-col" style={{ gap: 8 }}>
      {citations.map((c) => (
        <div
          key={c.chunkId}
          className="flex flex-col"
          style={{
            gap: 4,
            padding: "10px 12px",
            borderRadius: "var(--radius-md)",
            background: "var(--color-item-bg)",
            border: "1px solid var(--border-default)",
          }}
        >
          <span className="flex flex-wrap items-center" style={{ gap: 8 }}>
            <span style={{ ...PILL, background: "var(--accent-primary-soft)", color: "var(--accent-primary)" }}>
              {c.section}
            </span>
            <span className="text-[11px]" style={{ color: "var(--text-muted)" }}>
              {c.score.toFixed(3)} · p.{c.page}
            </span>
            <span className="text-[11px]" style={{ color: "var(--text-muted)" }}>
              {c.paperTitle}
            </span>
          </span>
          <span className="text-xs" style={{ color: "var(--text-secondary)", lineHeight: 1.65 }}>
            {c.text}
          </span>
        </div>
      ))}
    </div>
  );
}

export default function KnowledgeBoard({ stats }: { stats: KnowledgeStats }) {
  const [query, setQuery] = useState("");
  const [hits, setHits] = useState<KnowledgeCitation[] | null>(null);
  const [searching, setSearching] = useState(false);

  const [question, setQuestion] = useState("");
  const [answer, setAnswer] = useState<KnowledgeAnswer | null>(null);
  const [asking, setAsking] = useState(false);

  const [error, setError] = useState<string | null>(null);

  /** 嵌入模型退化告警：hash-384 是哈希伪嵌入（无语义），检索"看起来能用但不准"。 */
  const embedderDegraded = stats.modelName.includes("hash");

  async function onSearch() {
    const q = query.trim();
    if (!q || searching) return;
    setSearching(true);
    setError(null);
    try {
      setHits(await searchKnowledge(q, 5));
    } catch (e) {
      setError(e instanceof Error ? e.message : "检索失败");
      setHits(null);
    } finally {
      setSearching(false);
    }
  }

  async function onAsk() {
    const q = question.trim();
    if (!q || asking) return;
    setAsking(true);
    setError(null);
    try {
      setAnswer(await askKnowledge(q, { topK: 5 }));
    } catch (e) {
      setError(e instanceof Error ? e.message : "提问失败");
      setAnswer(null);
    } finally {
      setAsking(false);
    }
  }

  return (
    <div className="flex flex-col" style={{ gap: 18 }}>
      {/* ═══════ 库里有什么 ═══════ */}
      <div className="flex flex-col" style={{ ...cardStyle, gap: 12 }}>
        <span className="text-[15px] font-semibold" style={{ color: "var(--text-primary)" }}>
          知识库
        </span>
        <div className="flex flex-wrap" style={{ gap: 20 }}>
          {[
            { label: "论文", value: String(stats.paperCount) },
            { label: "分块", value: String(stats.chunkCount) },
            { label: "已索引", value: String(stats.indexedChunkCount) },
            { label: "覆盖率", value: `${(stats.coverage * 100).toFixed(1)}%` },
          ].map((m) => (
            <div key={m.label} className="flex flex-col" style={{ gap: 2 }}>
              <span className="text-[11px]" style={{ color: "var(--text-muted)" }}>
                {m.label}
              </span>
              <span className="text-[17px] font-semibold" style={{ color: "var(--text-primary)" }}>
                {m.value}
              </span>
            </div>
          ))}
        </div>
        <span className="text-[11px]" style={{ color: "var(--text-muted)" }}>
          嵌入模型：{stats.modelName || "（未上报）"}
        </span>
        {embedderDegraded && (
          <Notice tone="amber">
            当前嵌入模型是 <b>hash 伪嵌入</b>（无语义），检索会「看起来能用但不准」。
            修复：安装 sentence-transformers，在 .env 设 HF_ENDPOINT 指向可用镜像，
            然后调 POST /api/paper/index 并传 force_rebuild=true 重建索引。
          </Notice>
        )}
      </div>

      {error && <Notice tone="rose">操作失败：{error}</Notice>}

      {/* ═══════ 这个概念在哪：检索 ═══════ */}
      <div className="flex flex-col" style={{ ...cardStyle, gap: 12 }}>
        <span className="text-[15px] font-semibold" style={{ color: "var(--text-primary)" }}>
          检索
        </span>
        <div className="flex flex-wrap" style={{ gap: 8 }}>
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter") void onSearch();
            }}
            placeholder="例如：low-rank adaptation matrices"
            className="flex-1 text-[13px]"
            style={{
              minWidth: 240,
              padding: "9px 12px",
              borderRadius: "var(--radius-md)",
              border: "1px solid var(--border-default)",
              background: "var(--color-item-bg)",
              color: "var(--text-primary)",
            }}
          />
          <button
            onClick={() => void onSearch()}
            disabled={searching || !query.trim()}
            className="text-[13px] font-medium"
            style={{
              padding: "9px 18px",
              borderRadius: "var(--radius-md)",
              border: "none",
              background: "var(--accent-primary)",
              color: "var(--text-inverse)",
              cursor: searching ? "wait" : "pointer",
              opacity: searching || !query.trim() ? 0.6 : 1,
            }}
          >
            {searching ? "检索中…" : "检索"}
          </button>
        </div>
        {hits !== null &&
          (hits.length === 0 ? (
            <span className="text-xs" style={{ color: "var(--text-muted)" }}>
              没有命中。换个说法，或先导入更多论文。
            </span>
          ) : (
            <CitationList citations={hits} />
          ))}
      </div>

      {/* ═══════ 卡住了问一句：问答 ═══════ */}
      <div className="flex flex-col" style={{ ...cardStyle, gap: 12 }}>
        <span className="text-[15px] font-semibold" style={{ color: "var(--text-primary)" }}>
          提问
        </span>
        <textarea
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          placeholder="例如：What is the main advantage of DPO over RLHF?"
          rows={2}
          className="text-[13px]"
          style={{
            padding: "9px 12px",
            borderRadius: "var(--radius-md)",
            border: "1px solid var(--border-default)",
            background: "var(--color-item-bg)",
            color: "var(--text-primary)",
            resize: "vertical",
            fontFamily: "inherit",
          }}
        />
        <div>
          <button
            onClick={() => void onAsk()}
            disabled={asking || !question.trim()}
            className="text-[13px] font-medium"
            style={{
              padding: "9px 18px",
              borderRadius: "var(--radius-md)",
              border: "none",
              background: "var(--accent-primary)",
              color: "var(--text-inverse)",
              cursor: asking ? "wait" : "pointer",
              opacity: asking || !question.trim() ? 0.6 : 1,
            }}
          >
            {asking ? "生成中…（约 10-60 秒）" : "提问"}
          </button>
        </div>

        {answer && (
          <div className="flex flex-col" style={{ gap: 12 }}>
            <div className="flex flex-wrap items-center" style={{ gap: 8 }}>
              {(() => {
                const meta = CONFIDENCE_META[answer.confidence] ?? CONFIDENCE_META.low;
                return (
                  <span style={{ ...PILL, background: meta.soft, color: meta.color }}>
                    置信度 {meta.label}
                  </span>
                );
              })()}
              <span className="text-[11px]" style={{ color: "var(--text-muted)" }}>
                命中 {answer.hitCount} 块
              </span>
              {answer.answerMode === "rule" && (
                <span
                  style={{
                    ...PILL,
                    background: "var(--accent-warning-soft)",
                    color: "var(--accent-warning)",
                  }}
                >
                  片段兜底（LLM 不可用）
                </span>
              )}
            </div>
            <div
              className="text-[13px]"
              style={{
                color: "var(--text-secondary)",
                lineHeight: 1.75,
                whiteSpace: "pre-wrap",
                padding: "12px 14px",
                borderRadius: "var(--radius-md)",
                background: "var(--color-item-bg)",
                border: "1px solid var(--border-default)",
              }}
            >
              {answer.answer}
            </div>
            <span className="text-xs" style={{ color: "var(--text-muted)" }}>
              引用来源
            </span>
            <CitationList citations={answer.citations} />
          </div>
        )}
      </div>
    </div>
  );
}
