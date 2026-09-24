"use client";

import { useState, type CSSProperties } from "react";
import { useRouter } from "next/navigation";
import ExperimentTable from "@/components/ExperimentTable";
import {
  createExperiment,
  deleteExperiment,
} from "@/services/experimentService";
import type { Experiment, ExperimentKind, ExperimentVariant } from "@/types";

type Props = {
  experiments: Experiment[];
};

const KIND_LABEL: Record<ExperimentKind, string> = {
  finetune: "微调对比",
  benchmark: "推理基准",
  ablation: "消融实验",
};

const KIND_COLOR: Record<ExperimentKind, string> = {
  finetune: "var(--color-violet)",
  benchmark: "var(--color-sky)",
  ablation: "var(--accent-warning)",
};

const cardStyle: CSSProperties = {
  background: "var(--surface-card)",
  border: "1px solid var(--border-default)",
  borderRadius: "var(--radius-lg)",
  padding: "var(--spacing-lg)",
};

const LORA_TEMPLATE = JSON.stringify(
  [
    { name: "Full SFT", trainable_params: "7.0B", gpu_mem: "38GB", time: "5.2h", result: "baseline" },
    { name: "LoRA r=16", trainable_params: "42M", gpu_mem: "19GB", time: "1.8h", result: "≈ baseline" },
    { name: "QLoRA r=16", trainable_params: "42M", gpu_mem: "11GB", time: "2.1h", result: "略降 1.2%" },
  ],
  null,
  2,
);

/** 实验记录板（P2）：渲染已有实验的对比表 + 新增表单。 */
export default function ExperimentBoard({ experiments }: Props) {
  const router = useRouter();
  const [showForm, setShowForm] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [name, setName] = useState("");
  const [daySeq, setDaySeq] = useState("22");
  const [kind, setKind] = useState<ExperimentKind>("finetune");
  const [skillName, setSkillName] = useState("LoRA/QLoRA");
  const [variantsText, setVariantsText] = useState(LORA_TEMPLATE);
  const [metricsText, setMetricsText] = useState("[]");
  const [conclusion, setConclusion] = useState("");

  async function submit() {
    setBusy(true);
    setError(null);
    let variants: ExperimentVariant[];
    let metrics: { name: string; value: unknown; unit?: string }[];
    try {
      variants = JSON.parse(variantsText);
      metrics = JSON.parse(metricsText || "[]");
    } catch {
      setError("variants / metrics 必须是合法 JSON");
      setBusy(false);
      return;
    }
    if (!name.trim()) {
      setError("请填写实验名");
      setBusy(false);
      return;
    }
    try {
      await createExperiment({
        daySeq: Number(daySeq),
        name: name.trim(),
        kind,
        skillName: skillName.trim() || null,
        variants,
        metrics,
        conclusion: conclusion.trim() || null,
      });
      setShowForm(false);
      setName("");
      setConclusion("");
      router.refresh();
    } catch (e) {
      setError(e instanceof Error ? e.message : "提交失败");
    } finally {
      setBusy(false);
    }
  }

  async function remove(id: string) {
    if (busy) return;
    setBusy(true);
    try {
      await deleteExperiment(id);
      router.refresh();
    } catch (e) {
      setError(e instanceof Error ? e.message : "删除失败");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="flex flex-col" style={{ gap: 18 }}>
      <div className="flex items-center justify-between">
        <span className="text-sm" style={{ color: "var(--text-muted)" }}>
          实验是一等公民（决策 4）：把「我跑了 Qwen」变成「我研究了 PEFT 对成本与效果的影响」。
        </span>
        <button
          disabled={busy}
          onClick={() => setShowForm((v) => !v)}
          className="border-none text-xs font-medium"
          style={{
            padding: "7px 14px",
            borderRadius: "var(--radius-pill)",
            background: "var(--accent-primary-soft)",
            color: "var(--accent-primary)",
            cursor: "pointer",
          }}
        >
          {showForm ? "收起" : "+ 新增实验"}
        </button>
      </div>

      {showForm && (
        <div className="flex flex-col" style={{ ...cardStyle, gap: 12 }}>
          <div className="flex flex-wrap" style={{ gap: 12 }}>
            <Field label="实验名">
              <input
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="如 LoRA vs QLoRA"
                style={inputStyle}
              />
            </Field>
            <Field label="课程日 Day">
              <input
                value={daySeq}
                onChange={(e) => setDaySeq(e.target.value)}
                type="number"
                min={1}
                max={30}
                style={{ ...inputStyle, width: 90 }}
              />
            </Field>
            <Field label="类型">
              <select
                value={kind}
                onChange={(e) => setKind(e.target.value as ExperimentKind)}
                style={inputStyle}
              >
                <option value="finetune">微调对比</option>
                <option value="benchmark">推理基准</option>
                <option value="ablation">消融实验</option>
              </select>
            </Field>
            <Field label="关联技能">
              <input
                value={skillName}
                onChange={(e) => setSkillName(e.target.value)}
                placeholder="如 LoRA/QLoRA"
                style={inputStyle}
              />
            </Field>
          </div>

          <Field label="变体（JSON 数组，每项为对比表中的一行）">
            <textarea
              value={variantsText}
              onChange={(e) => setVariantsText(e.target.value)}
              rows={8}
              style={{ ...inputStyle, fontFamily: "ui-monospace, monospace", fontSize: 12 }}
            />
          </Field>

          <Field label="指标（JSON 数组，可选）">
            <textarea
              value={metricsText}
              onChange={(e) => setMetricsText(e.target.value)}
              rows={3}
              style={{ ...inputStyle, fontFamily: "ui-monospace, monospace", fontSize: 12 }}
            />
          </Field>

          <Field label="结论（可选）">
            <textarea
              value={conclusion}
              onChange={(e) => setConclusion(e.target.value)}
              rows={2}
              style={inputStyle}
            />
          </Field>

          <div className="flex items-center" style={{ gap: 10 }}>
            <button
              disabled={busy}
              onClick={submit}
              className="border-none text-xs font-semibold"
              style={{
                padding: "8px 16px",
                borderRadius: "var(--radius-pill)",
                background: "var(--accent-primary)",
                color: "var(--text-inverse)",
                cursor: busy ? "wait" : "pointer",
              }}
            >
              {busy ? "提交中…" : "保存实验"}
            </button>
            <button
              onClick={() => setVariantsText(LORA_TEMPLATE)}
              className="border-none text-xs font-medium"
              style={{
                padding: "8px 12px",
                borderRadius: "var(--radius-pill)",
                background: "var(--color-item-bg)",
                border: "1px solid var(--border-default)",
                color: "var(--text-muted)",
                cursor: "pointer",
              }}
            >
              填入 LoRA vs QLoRA 模板
            </button>
            {error && (
              <span className="text-xs" style={{ color: "var(--accent-danger)" }}>
                {error}
              </span>
            )}
          </div>
        </div>
      )}

      {experiments.length === 0 ? (
        <div className="flex flex-col" style={{ ...cardStyle, gap: 8 }}>
          <span className="text-[15px] font-semibold" style={{ color: "var(--text-primary)" }}>
            还没有实验记录
          </span>
          <span className="text-xs" style={{ color: "var(--text-muted)", lineHeight: 1.7 }}>
            点「+ 新增实验」填一次 LoRA vs QLoRA / SFT vs LoRA / Transformers vs vLLM，
            页面会直接渲染出对比表。Day 12 / 22 / 23 都要求落实验表。
          </span>
        </div>
      ) : (
        experiments.map((exp) => (
          <div key={exp.id} className="flex flex-col" style={{ ...cardStyle, gap: 12 }}>
            <div className="flex flex-wrap items-center justify-between" style={{ gap: 10 }}>
              <div className="flex items-center" style={{ gap: 10, flexWrap: "wrap" }}>
                <span
                  className="font-semibold"
                  style={{ fontSize: 16, color: "var(--text-primary)" }}
                >
                  {exp.name}
                </span>
                <span
                  className="inline-flex items-center"
                  style={{
                    padding: "3px 9px",
                    borderRadius: "var(--radius-pill)",
                    fontSize: 11,
                    fontWeight: 600,
                    background: "var(--color-item-bg)",
                    border: "1px solid var(--border-default)",
                    color: "var(--text-muted)",
                  }}
                >
                  Day {exp.daySeq}
                </span>
                <span
                  className="inline-flex items-center"
                  style={{
                    padding: "3px 9px",
                    borderRadius: "var(--radius-pill)",
                    fontSize: 11,
                    fontWeight: 600,
                    color: "var(--text-inverse)",
                    background: KIND_COLOR[exp.kind],
                  }}
                >
                  {KIND_LABEL[exp.kind]}
                </span>
                {exp.skillName && (
                  <span
                    className="inline-flex items-center"
                    style={{
                      padding: "3px 9px",
                      borderRadius: "var(--radius-pill)",
                      fontSize: 11,
                      background: "var(--accent-success-soft)",
                      color: "var(--accent-success)",
                    }}
                  >
                    {exp.skillName}
                  </span>
                )}
              </div>
              <button
                onClick={() => remove(exp.id)}
                disabled={busy}
                className="border-none text-xs"
                style={{
                  background: "transparent",
                  color: "var(--text-muted)",
                  cursor: "pointer",
                }}
              >
                删除
              </button>
            </div>

            <ExperimentTable variants={exp.variants} />

            {exp.metrics.length > 0 && (
              <div className="flex flex-wrap" style={{ gap: 8 }}>
                {exp.metrics.map((m, i) => (
                  <span
                    key={i}
                    className="inline-flex items-center"
                    style={{
                      padding: "3px 9px",
                      borderRadius: "var(--radius-pill)",
                      fontSize: 11,
                      background: "var(--color-item-bg)",
                      border: "1px solid var(--border-default)",
                      color: "var(--text-muted)",
                    }}
                  >
                    {m.name}: {String(m.value)}
                    {m.unit ? ` ${m.unit}` : ""}
                  </span>
                ))}
              </div>
            )}

            {exp.conclusion && (
              <p className="text-[13px]" style={{ color: "var(--text-secondary)", lineHeight: 1.7, margin: 0 }}>
                {exp.conclusion}
              </p>
            )}
          </div>
        ))
      )}
    </div>
  );
}

const inputStyle: CSSProperties = {
  padding: "8px 10px",
  borderRadius: "var(--radius-md)",
  border: "1px solid var(--border-default)",
  background: "var(--surface-card)",
  color: "var(--text-primary)",
  fontSize: 13,
  width: "100%",
  fontFamily: "inherit",
};

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <label className="flex flex-col" style={{ gap: 4, flex: "1 1 200px", minWidth: 0 }}>
      <span className="text-[11px] font-medium" style={{ color: "var(--text-muted)" }}>
        {label}
      </span>
      {children}
    </label>
  );
}
