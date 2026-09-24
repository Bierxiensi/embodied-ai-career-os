"use client";

import { useState, type ReactNode } from "react";

type Variant = "underline" | "pill";

interface TabItem {
  key: string;
  label: string;
  content: ReactNode;
}

interface TabsProps {
  items: TabItem[];
  variant?: Variant;
  activeKey?: string;
  onChange?: (key: string) => void;
  className?: string;
  style?: React.CSSProperties;
}

export default function Tabs({ items, variant = "underline", activeKey, onChange, className, style }: TabsProps) {
  const [internalKey, setInternalKey] = useState(items[0]?.key);
  const current = activeKey ?? internalKey;

  const handleChange = (key: string) => {
    setInternalKey(key);
    onChange?.(key);
  };

  const activeItem = items.find((item) => item.key === current);

  return (
    <div className={className} style={{ display: "flex", flexDirection: "column", ...style }}>
      <div
        role="tablist"
        style={{
          display: "flex",
          gap: variant === "pill" ? 4 : 0,
          borderBottom: variant === "underline" ? "1px solid var(--border-subtle)" : "none",
          padding: variant === "pill" ? 3 : 0,
          background: variant === "pill" ? "var(--surface-card)" : "transparent",
          borderRadius: variant === "pill" ? "var(--radius-item)" : 0,
        }}
      >
        {items.map((item) => {
          const isActive = item.key === current;

          return (
            <button
              key={item.key}
              role="tab"
              aria-selected={isActive}
              onClick={() => handleChange(item.key)}
              style={{
                padding: variant === "pill" ? "8px 16px" : "10px 16px",
                fontSize: 13,
                fontWeight: isActive ? 600 : 400,
                border: "none",
                borderRadius: variant === "pill" ? "calc(var(--radius-item) - 2px)" : 0,
                background: isActive
                  ? variant === "pill"
                    ? "var(--surface-card)"
                    : "transparent"
                  : "transparent",
                color: isActive ? "var(--accent-primary)" : "var(--text-muted)",
                cursor: "pointer",
                transition: "120ms ease-out",
                position: "relative",
                boxShadow: variant === "pill" && isActive ? "var(--shadow-card)" : "none",
              }}
            >
              {item.label}
              {variant === "underline" && isActive && (
                <span
                  style={{
                    position: "absolute",
                    bottom: -1,
                    left: 0,
                    right: 0,
                    height: 2,
                    background: "var(--accent-primary)",
                    borderRadius: 1,
                  }}
                />
              )}
            </button>
          );
        })}
      </div>
      <div role="tabpanel" style={{ paddingTop: 16 }}>
        {activeItem?.content}
      </div>
    </div>
  );
}
