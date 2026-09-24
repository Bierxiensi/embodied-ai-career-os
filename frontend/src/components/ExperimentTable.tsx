import type { ExperimentVariant } from "@/types";

const thStyle: React.CSSProperties = {
  textAlign: "left",
  padding: "8px 12px",
  borderBottom: "1px solid var(--border-default)",
  color: "var(--text-muted)",
  fontSize: 11,
  fontWeight: 600,
  whiteSpace: "nowrap",
  background: "var(--color-item-bg)",
};

const tdStyle: React.CSSProperties = {
  padding: "8px 12px",
  borderBottom: "1px solid var(--border-subtle)",
  color: "var(--text-secondary)",
  fontSize: 12,
  whiteSpace: "nowrap",
};

/** 实验对比表渲染器（P2 验收核心）：把 variants JSON 直接渲染成对比表。
 *
 * 列 = 所有变体 key 的并集；行 = 每个变体。这样
 * 「填一次 LoRA vs QLoRA 实验，页面直接渲染出对比表」无需任何手工拼表。
 */
export default function ExperimentTable({ variants }: { variants: ExperimentVariant[] }) {
  if (!variants || variants.length === 0) {
    return (
      <span className="text-xs" style={{ color: "var(--text-muted)" }}>
        暂无变体数据（variants 为空）
      </span>
    );
  }

  const keys = Array.from(new Set(variants.flatMap((v) => Object.keys(v))));

  return (
    <div style={{ overflowX: "auto" }}>
      <table style={{ borderCollapse: "collapse", width: "100%" }}>
        <thead>
          <tr>
            {keys.map((k) => (
              <th key={k} style={thStyle}>
                {k}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {variants.map((v, i) => (
            <tr key={i}>
              {keys.map((k) => (
                <td key={k} style={tdStyle}>
                  {v[k] === undefined || v[k] === null ? "—" : String(v[k])}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
