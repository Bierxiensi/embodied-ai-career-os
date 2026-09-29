"use client";

/** 作品集组装面板：一键从证据库生成 13 节 README（不虚构，缺就如实写缺）。 */

import { useState } from "react";
import { assemblePortfolio, type Portfolio } from "@/services/portfolioService";

export default function PortfolioPanel() {
  const [portfolio, setPortfolio] = useState<Portfolio | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function assemble() {
    setBusy(true);
    setError(null);
    try {
      setPortfolio(await assemblePortfolio());
    } catch {
      setError("组装失败（后端不可用）");
    } finally {
      setBusy(false);
    }
  }

  return (
    <section
      className="flex flex-col"
      style={{ gap: 12, padding: 24, background: "var(--surface-card)", borderRadius: "var(--radius-lg)" }}
    >
      <div className="flex items-center" style={{ gap: 12 }}>
        <h2 className="text-base font-semibold">作品集</h2>
        <button
          type="button"
          disabled={busy}
          onClick={assemble}
          style={{
            padding: "6px 18px",
            borderRadius: "var(--radius-pill)",
            background: "var(--accent-primary)",
            color: "var(--text-inverse)",
            border: "none",
            cursor: busy ? "not-allowed" : "pointer",
            opacity: busy ? 0.7 : 1,
          }}
        >
          {busy ? "组装中..." : "组装 13 节 README"}
        </button>
        {portfolio ? (
          <span className="text-xs" style={{ color: "var(--text-muted)" }}>
            证据条目 {portfolio.evidenceCount} · 就绪技能 {portfolio.readySkills.length} 项
          </span>
        ) : null}
      </div>
      {error ? <p className="text-xs" style={{ color: "var(--accent-danger)" }}>{error}</p> : null}
      {portfolio ? (
        <div className="flex flex-col" style={{ gap: 8 }}>
          {portfolio.sections.map((s) => (
            <details key={s.name} style={{ border: "1px solid var(--border-default)", borderRadius: "var(--radius-md)", padding: 12 }}>
              <summary className="text-sm font-semibold cursor-pointer">{s.name}</summary>
              <p className="mt-2 text-xs" style={{ whiteSpace: "pre-wrap", color: "var(--text-muted)" }}>
                {s.content}
              </p>
            </details>
          ))}
        </div>
      ) : null}
    </section>
  );
}
