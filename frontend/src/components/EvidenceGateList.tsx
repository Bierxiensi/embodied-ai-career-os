"use client";

/** 证据门清单：每条能力主张的 L 级与出处（spec §2.3 差距可量化）。 */

import { useEffect, useState } from "react";
import { getEvidenceList, type EvidenceRow } from "@/services/portfolioService";

const GATE_LABEL = ["未入门", "L1 能解释", "L2 能实现", "L3 能实验", "L4 能研究"];

export default function EvidenceGateList() {
  const [rows, setRows] = useState<EvidenceRow[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getEvidenceList().then(setRows).catch(() => setError("证据门数据加载失败"));
  }, []);

  return (
    <section
      className="flex flex-col"
      style={{ gap: 12, padding: 24, background: "var(--surface-card)", borderRadius: "var(--radius-lg)" }}
    >
      <h2 className="text-base font-semibold">证据门（{rows.filter((r) => r.gate >= 1).length} 项有证据）</h2>
      {error ? <p className="text-xs" style={{ color: "var(--accent-danger)" }}>{error}</p> : null}
      <ul className="flex flex-col" style={{ gap: 8, listStyle: "none", padding: 0 }}>
        {rows.map((r) => (
          <li key={r.skill} className="flex items-center justify-between" style={{ gap: 12 }}>
            <span className="text-sm">{r.skill}</span>
            <span
              className="text-xs"
              style={{
                padding: "2px 10px",
                borderRadius: "var(--radius-pill)",
                background: r.gate >= 2 ? "var(--accent-primary-soft, #DBEAFE)" : "var(--surface-muted, #F4F4F5)",
                color: r.gate >= 2 ? "var(--accent-primary)" : "var(--text-muted)",
              }}
            >
              {GATE_LABEL[Math.min(r.gate, 4)]}
            </span>
          </li>
        ))}
      </ul>
    </section>
  );
}
