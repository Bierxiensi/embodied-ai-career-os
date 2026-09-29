"use client";

/** SM-2 复习队列：今日到期卡逐张过，4 档评分推进调度。
 * 「记住 ≠ 看过」——第三问的日常 10-15 分钟入口（spec §3.2）。 */

import { useEffect, useState } from "react";
import { listDueCards, reviewCard, type ReviewCardT } from "@/services/masteryService";

const RATINGS = [
  { key: "again", label: "忘了", color: "var(--accent-danger)" },
  { key: "hard", label: "模糊", color: "var(--accent-warning, #D97706)" },
  { key: "good", label: "记得", color: "var(--accent-primary)" },
  { key: "easy", label: "秒答", color: "var(--accent-success, #16A34A)" },
] as const;

export default function ReviewQueue() {
  const [cards, setCards] = useState<ReviewCardT[]>([]);
  const [dueCount, setDueCount] = useState(0);
  const [flipped, setFlipped] = useState(false);
  const [busy, setBusy] = useState(false);

  // 数据拉取走 promise 回调（react-hooks/set-state-in-effect：effect 内不得同步 setState）
  function refresh(): Promise<void> {
    return listDueCards()
      .then(({ cards: list, dueCount: count }) => {
        setCards(list);
        setDueCount(count);
      })
      .catch(() => {
        setCards([]);
        setDueCount(0);
      })
      .then(() => {
        setFlipped(false);
      });
  }

  useEffect(() => {
    void refresh();
  }, []);

  const current = cards[0];

  async function rate(rating: (typeof RATINGS)[number]["key"]) {
    if (!current) return;
    setBusy(true);
    try {
      await reviewCard(current.id, rating);
      await refresh();
    } finally {
      setBusy(false);
    }
  }

  return (
    <section
      className="flex flex-col"
      style={{ gap: 12, padding: 24, background: "var(--surface-card)", borderRadius: "var(--radius-lg)" }}
    >
      <h2 className="text-base font-semibold">今日复习（{dueCount} 张到期）</h2>
      {dueCount > cards.length ? (
        <p className="text-xs" style={{ color: "var(--text-muted)" }}>
          显示前 {cards.length} 张
        </p>
      ) : null}
      {cards.length === 0 ? (
        <p className="text-xs" style={{ color: "var(--text-muted)" }}>
          复习队列已清空——做完今天的掌握单元后，概念卡会自动入队。
        </p>
      ) : (
        <>
          <div
            onClick={() => setFlipped((f) => !f)}
            style={{
              padding: 24,
              minHeight: 96,
              borderRadius: "var(--radius-md)",
              border: "1px solid var(--border-default)",
              background: "var(--surface-canvas)",
              cursor: "pointer",
            }}
          >
            <p className="text-sm font-semibold">{current.front}</p>
            {flipped ? (
              <p className="mt-3 text-sm" style={{ color: "var(--text-muted)", whiteSpace: "pre-wrap" }}>
                {current.back}
              </p>
            ) : (
              <p className="mt-3 text-xs" style={{ color: "var(--text-muted)" }}>
                点击卡片看答案
              </p>
            )}
          </div>
          <div className="flex flex-wrap" style={{ gap: 8 }}>
            {RATINGS.map((r) => (
              <button
                key={r.key}
                type="button"
                disabled={busy || !flipped}
                onClick={() => rate(r.key)}
                style={{
                  padding: "6px 18px",
                  borderRadius: "var(--radius-pill)",
                  border: `1px solid ${r.color}`,
                  color: r.color,
                  background: "transparent",
                  cursor: busy || !flipped ? "not-allowed" : "pointer",
                  opacity: busy || !flipped ? 0.5 : 1,
                }}
              >
                {r.label}
              </button>
            ))}
          </div>
        </>
      )}
    </section>
  );
}
