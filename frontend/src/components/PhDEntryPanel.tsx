"use client";

/** 博士模块录入面板（2026-09-22 用户裁决：录入界面由系统提供，真实数据用户自己喂）。
 *
 * 两个表单：新增院校/机会（PhDTarget）、新增导师（PhDAdvisor）。
 * 提交成功后 router.refresh() 重拉服务端数据（看板通过 useEffect 同步 initialAdvisors）。
 * 样式纪律：一律 var(--color-*)，禁硬编码 hex；白底卡片 + hairline + 圆角。
 */

import { useState } from "react";
import { useRouter } from "next/navigation";

import {
  createPhdAdvisor,
  createPhdTarget,
  type PhDTargetDTO,
  type ResearchDirectionDTO,
} from "@/services/phdService";

const TIER_OPTIONS = ["985", "211", "双一流", "中科院", "市属", "普通", "海外"];
const PUB_OPTIONS = [
  { value: "none", label: "无硬性要求" },
  { value: "ei", label: "EI 即可" },
  { value: "sci", label: "要求 SCI" },
];
const TITLE_OPTIONS = ["教授", "副教授", "研究员", "助理教授", "讲师"];

const inputStyle: React.CSSProperties = {
  padding: "7px 10px",
  fontSize: 13,
  border: "1px solid var(--border-default)",
  borderRadius: 8,
  background: "var(--surface-card)",
  color: "var(--text-primary)",
  width: "100%",
};

const labelStyle: React.CSSProperties = {
  fontSize: 11,
  color: "var(--text-muted)",
  display: "flex",
  flexDirection: "column",
  gap: 4,
};

const btnStyle: React.CSSProperties = {
  padding: "8px 16px",
  borderRadius: 10,
  border: "none",
  background: "var(--accent-primary)",
  color: "var(--text-inverse)",
  fontSize: 13,
  fontWeight: 600,
  cursor: "pointer",
};

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <label style={labelStyle}>
      {label}
      {children}
    </label>
  );
}

export default function PhDEntryPanel({
  directions,
  targets,
}: {
  directions: ResearchDirectionDTO[];
  targets: PhDTargetDTO[];
}) {
  const router = useRouter();
  const [open, setOpen] = useState(false);
  const [tab, setTab] = useState<"target" | "advisor">("advisor");
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  // ── 机会表单状态 ──
  const [t, setT] = useState({
    institution: "",
    city: "北京",
    tier: "211",
    direction_key: "",
    in_service_friendly: false,
    min_publication: "none",
    application_deadline: "",
    notes: "",
  });

  // ── 导师表单状态 ──
  const [a, setA] = useState({
    target_id: "",
    name: "",
    title: "教授",
    research_area: "",
    recruiting: true,
    in_service_friendly: false,
    homepage: "",
    notes: "",
    contacted: false,
  });

  const submitTarget = async () => {
    if (!t.institution.trim()) {
      setMessage("院校名不能为空");
      return;
    }
    setBusy(true);
    setMessage(null);
    try {
      await createPhdTarget({
        institution: t.institution.trim(),
        city: t.city || null,
        tier: t.tier || null,
        direction_key: t.direction_key || null,
        in_service_friendly: t.in_service_friendly,
        min_publication: t.min_publication,
        application_deadline: t.application_deadline || null,
        notes: t.notes || null,
      });
      setMessage(`已录入机会：${t.institution}`);
      setT({ ...t, institution: "", notes: "" });
      router.refresh();
    } catch (e) {
      setMessage(`录入失败：${e instanceof Error ? e.message : String(e)}`);
    } finally {
      setBusy(false);
    }
  };

  const submitAdvisor = async () => {
    if (!a.name.trim()) {
      setMessage("导师姓名不能为空");
      return;
    }
    setBusy(true);
    setMessage(null);
    try {
      await createPhdAdvisor({
        target_id: a.target_id ? Number(a.target_id) : null,
        name: a.name.trim(),
        title: a.title || null,
        research_area: a.research_area || null,
        recruiting: a.recruiting,
        in_service_friendly: a.in_service_friendly,
        homepage: a.homepage || null,
        notes: a.notes || null,
        contacted: a.contacted,
        contact_date: a.contacted ? new Date().toISOString() : null,
      });
      setMessage(`已录入导师：${a.name}`);
      setA({ ...a, name: "", research_area: "", homepage: "", notes: "", contacted: false });
      router.refresh();
    } catch (e) {
      setMessage(`录入失败：${e instanceof Error ? e.message : String(e)}`);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div
      style={{
        background: "var(--surface-card)",
        border: "1px solid var(--border-default)",
        borderRadius: "var(--radius-lg, 16px)",
        padding: 16,
        margin: "0 24px 16px",
      }}
    >
      <button
        onClick={() => setOpen(!open)}
        className="text-sm font-semibold"
        style={{
          background: "none",
          border: "none",
          cursor: "pointer",
          color: "var(--accent-primary)",
          padding: 0,
        }}
      >
        {open ? "▾ 收起录入面板" : "▸ 录入新数据（院校 / 导师）"}
      </button>

      {open && (
        <div className="flex flex-col" style={{ gap: 14, marginTop: 14 }}>
          <div className="flex" style={{ gap: 8 }}>
            {(["advisor", "target"] as const).map((k) => (
              <button
                key={k}
                onClick={() => setTab(k)}
                className="text-xs font-medium"
                style={{
                  padding: "5px 12px",
                  borderRadius: "var(--radius-pill)",
                  border: "1px solid var(--border-default)",
                  cursor: "pointer",
                  background: tab === k ? "var(--accent-primary-soft)" : "transparent",
                  color: tab === k ? "var(--accent-primary)" : "var(--text-muted)",
                }}
              >
                {k === "advisor" ? "新增导师" : "新增院校/机会"}
              </button>
            ))}
          </div>

          {tab === "target" ? (
            <div
              className="grid"
              style={{ gap: 10, gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))" }}
            >
              <Field label="院校/单位 *">
                <input style={inputStyle} value={t.institution} onChange={(e) => setT({ ...t, institution: e.target.value })} placeholder="如 北京科技大学" />
              </Field>
              <Field label="城市">
                <input style={inputStyle} value={t.city} onChange={(e) => setT({ ...t, city: e.target.value })} />
              </Field>
              <Field label="层次">
                <select style={inputStyle} value={t.tier} onChange={(e) => setT({ ...t, tier: e.target.value })}>
                  {TIER_OPTIONS.map((o) => <option key={o}>{o}</option>)}
                </select>
              </Field>
              <Field label="研究方向">
                <select style={inputStyle} value={t.direction_key} onChange={(e) => setT({ ...t, direction_key: e.target.value })}>
                  <option value="">（不指定）</option>
                  {directions.map((d) => <option key={d.key} value={d.key}>{d.name}</option>)}
                </select>
              </Field>
              <Field label="成果门槛">
                <select style={inputStyle} value={t.min_publication} onChange={(e) => setT({ ...t, min_publication: e.target.value })}>
                  {PUB_OPTIONS.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
                </select>
              </Field>
              <Field label="报名截止（空=常年）">
                <input type="date" style={inputStyle} value={t.application_deadline} onChange={(e) => setT({ ...t, application_deadline: e.target.value })} />
              </Field>
              <Field label="备注">
                <input style={inputStyle} value={t.notes} onChange={(e) => setT({ ...t, notes: e.target.value })} placeholder="申请-考核制 / 非全名额等" />
              </Field>
              <label className="flex items-center" style={{ gap: 6, fontSize: 12, color: "var(--text-secondary)", alignSelf: "end" }}>
                <input type="checkbox" checked={t.in_service_friendly} onChange={(e) => setT({ ...t, in_service_friendly: e.target.checked })} />
                在职/非全友好
              </label>
              <div style={{ gridColumn: "1 / -1" }}>
                <button style={btnStyle} disabled={busy} onClick={submitTarget}>
                  {busy ? "提交中…" : "录入机会"}
                </button>
              </div>
            </div>
          ) : (
            <div
              className="grid"
              style={{ gap: 10, gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))" }}
            >
              <Field label="姓名 *">
                <input style={inputStyle} value={a.name} onChange={(e) => setA({ ...a, name: e.target.value })} placeholder="真实姓名，或「XX大学·XX方向导师（待确认）」占位" />
              </Field>
              <Field label="所属院校/机会">
                <select style={inputStyle} value={a.target_id} onChange={(e) => setA({ ...a, target_id: e.target.value })}>
                  <option value="">（暂不关联）</option>
                  {targets.map((tg) => <option key={tg.id} value={tg.id}>{tg.institution}{tg.tier ? ` · ${tg.tier}` : ""}</option>)}
                </select>
              </Field>
              <Field label="职称">
                <select style={inputStyle} value={a.title} onChange={(e) => setA({ ...a, title: e.target.value })}>
                  {TITLE_OPTIONS.map((o) => <option key={o}>{o}</option>)}
                </select>
              </Field>
              <Field label="研究方向描述">
                <input style={inputStyle} value={a.research_area} onChange={(e) => setA({ ...a, research_area: e.target.value })} placeholder="如 多模态大模型 / 机器人学习" />
              </Field>
              <Field label="主页">
                <input style={inputStyle} value={a.homepage} onChange={(e) => setA({ ...a, homepage: e.target.value })} placeholder="https://…" />
              </Field>
              <Field label="备注">
                <input style={inputStyle} value={a.notes} onChange={(e) => setA({ ...a, notes: e.target.value })} />
              </Field>
              <div className="flex items-center" style={{ gap: 14, gridColumn: "1 / -1" }}>
                <label className="flex items-center" style={{ gap: 6, fontSize: 12, color: "var(--text-secondary)" }}>
                  <input type="checkbox" checked={a.recruiting} onChange={(e) => setA({ ...a, recruiting: e.target.checked })} />
                  在招
                </label>
                <label className="flex items-center" style={{ gap: 6, fontSize: 12, color: "var(--text-secondary)" }}>
                  <input type="checkbox" checked={a.in_service_friendly} onChange={(e) => setA({ ...a, in_service_friendly: e.target.checked })} />
                  在职友好
                </label>
                <label className="flex items-center" style={{ gap: 6, fontSize: 12, color: "var(--text-secondary)" }}>
                  <input type="checkbox" checked={a.contacted} onChange={(e) => setA({ ...a, contacted: e.target.checked })} />
                  已联系
                </label>
              </div>
              <div style={{ gridColumn: "1 / -1" }}>
                <button style={btnStyle} disabled={busy} onClick={submitAdvisor}>
                  {busy ? "提交中…" : "录入导师"}
                </button>
              </div>
            </div>
          )}

          {message && (
            <span className="text-xs" style={{ color: message.startsWith("录入失败") ? "var(--accent-danger)" : "var(--accent-success)" }}>
              {message}
            </span>
          )}
        </div>
      )}
    </div>
  );
}
