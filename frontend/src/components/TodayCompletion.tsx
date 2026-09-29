"use client";

/** 今日完成度：实质三选一（spec §3.2）——测验过 / Teach-Back 过 / 证据挂上。
 * 不再是布尔勾选：完成状态从真实记录派生，不可手点。 */

import type { LearningLog, MasteryUnit } from "@/types";

export default function TodayCompletion({
  unit,
  logs,
}: {
  unit: MasteryUnit | null;
  logs: LearningLog[];
}) {
  const quizPassed = (unit?.items ?? []).some((i) => i.isVerified);
  const teachBackDone = logs.some((l) => l.content.startsWith("Teach-Back ·"));
  const evidence = logs.some((l) => Boolean(l.artifactUrl));
  const done = quizPassed || teachBackDone || evidence;
  const criteria = [
    { ok: quizPassed, label: "测验实证过" },
    { ok: teachBackDone, label: "Teach-Back 过" },
    { ok: evidence, label: "证据已挂" },
  ];

  return (
    <section
      className="flex flex-col"
      style={{ gap: 8, padding: 16, background: "var(--surface-card)", borderRadius: "var(--radius-lg)" }}
    >
      <h3 className="text-sm font-semibold">
        今日完成：{done ? "✓ 已达成（三选一）" : "未达成——学完来真的，不勾选"}
      </h3>
      <div className="flex flex-wrap" style={{ gap: 8 }}>
        {criteria.map((c) => (
          <span
            key={c.label}
            className="text-xs"
            style={{
              padding: "2px 10px",
              borderRadius: "var(--radius-pill)",
              background: c.ok ? "var(--accent-primary-soft, #DBEFE)" : "var(--surface-muted, #F4F4F5)",
              color: c.ok ? "var(--accent-primary)" : "var(--text-muted)",
            }}
          >
            {c.ok ? "✓" : "○"} {c.label}
          </span>
        ))}
      </div>
    </section>
  );
}
