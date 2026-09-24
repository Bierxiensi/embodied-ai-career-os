"use client";

import { useState, useRef, useEffect } from "react";

type Size = "sm" | "md" | "lg";

interface SelectOption {
  value: string;
  label: string;
}

interface SelectProps {
  size?: Size;
  options: SelectOption[];
  searchable?: boolean;
  placeholder?: string;
  value?: string;
  onChange?: (value: string) => void;
  disabled?: boolean;
  className?: string;
  style?: React.CSSProperties;
}

const sizeMap: Record<Size, { padding: string; fontSize: number }> = {
  sm: { padding: "6px 10px", fontSize: 12 },
  md: { padding: "8px 12px", fontSize: 13 },
  lg: { padding: "12px 16px", fontSize: 15 },
};

export default function Select({
  size = "md",
  options,
  searchable,
  placeholder = "请选择",
  value,
  onChange,
  disabled,
  className,
  style,
}: SelectProps) {
  const [open, setOpen] = useState(false);
  const [search, setSearch] = useState("");
  const ref = useRef<HTMLDivElement>(null);
  const s = sizeMap[size];

  const selected = options.find((o) => o.value === value);
  const filtered = searchable
    ? options.filter((o) => o.label.toLowerCase().includes(search.toLowerCase()))
    : options;

  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, []);

  return (
    <div ref={ref} className={className} style={{ position: "relative", ...style }}>
      <button
        onClick={() => !disabled && setOpen(!open)}
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          width: "100%",
          padding: s.padding,
          fontSize: s.fontSize,
          borderRadius: "var(--radius-item)",
          border: "1px solid var(--border-default)",
          background: "var(--surface-card)",
          color: selected ? "var(--text-primary)" : "var(--text-muted)",
          cursor: disabled ? "not-allowed" : "pointer",
          opacity: disabled ? 0.5 : 1,
          transition: "120ms ease-out",
        }}
      >
        <span>{selected?.label ?? placeholder}</span>
        <span style={{ fontSize: 10, color: "var(--text-muted)" }}>▼</span>
      </button>

      {open && (
        <div
          style={{
            position: "absolute",
            top: "100%",
            left: 0,
            right: 0,
            marginTop: 4,
            background: "var(--surface-elevated)",
            border: "1px solid var(--border-default)",
            borderRadius: "var(--radius-item)",
            boxShadow: "var(--shadow-elevated)",
            zIndex: 1000,
            maxHeight: 240,
            overflow: "auto",
          }}
        >
          {searchable && (
            <div style={{ padding: 8, borderBottom: "1px solid var(--border-subtle)" }}>
              <input
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                placeholder="搜索..."
                autoFocus
                style={{
                  width: "100%",
                  padding: "6px 8px",
                  fontSize: s.fontSize,
                  border: "1px solid var(--border-default)",
                  borderRadius: "var(--radius-item)",
                  background: "var(--surface-card)",
                  color: "var(--text-primary)",
                  outline: "none",
                }}
              />
            </div>
          )}
          {filtered.map((o) => (
            <button
              key={o.value}
              onClick={() => {
                onChange?.(o.value);
                setOpen(false);
                setSearch("");
              }}
              style={{
                display: "block",
                width: "100%",
                padding: "8px 12px",
                fontSize: s.fontSize,
                border: "none",
                background: o.value === value ? "var(--accent-primary-soft)" : "transparent",
                color: o.value === value ? "var(--accent-primary)" : "var(--text-primary)",
                cursor: "pointer",
                textAlign: "left",
                fontWeight: o.value === value ? 600 : 400,
                transition: "120ms ease-out",
              }}
              onMouseEnter={(e) => {
                if (o.value !== value) e.currentTarget.style.background = "var(--surface-card)";
              }}
              onMouseLeave={(e) => {
                if (o.value !== value) e.currentTarget.style.background = "transparent";
              }}
            >
              {o.label}
            </button>
          ))}
          {filtered.length === 0 && (
            <div style={{ padding: "12px", fontSize: s.fontSize, color: "var(--text-muted)", textAlign: "center" }}>
              无匹配选项
            </div>
          )}
        </div>
      )}
    </div>
  );
}
