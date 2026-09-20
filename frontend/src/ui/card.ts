import type { CSSProperties } from "react";

/** 卡片外壳样式 — 所有 Dashboard 卡片和页面卡片统一使用。
 *
 * 用法：
 *   <div style={cardShell}>...</div>
 *   <div style={{ ...cardShell, padding: 32 }}>...</div>  // 覆盖个别属性
 */
export const cardShell: CSSProperties = {
  background: "var(--color-card)",
  border: "1px solid var(--color-hairline)",
  borderRadius: "var(--radius-card-lg)",
  padding: "var(--spacing-lg)",
};

/** 卡片内子项背景（任务行、活动行等）。 */
export const itemBg: CSSProperties = {
  background: "var(--color-item-bg)",
  borderRadius: "var(--radius-item-md)",
};
