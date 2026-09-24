"use client";

import { useState, type ReactNode } from "react";

interface AccordionItem {
  key: string;
  title: ReactNode;
  content: ReactNode;
}

interface AccordionProps {
  items: AccordionItem[];
  multiple?: boolean;
  className?: string;
  style?: React.CSSProperties;
}

export default function Accordion({ items, multiple, className, style }: AccordionProps) {
  const [openKeys, setOpenKeys] = useState<Set<string>>(new Set());

  const toggle = (key: string) => {
    setOpenKeys((prev) => {
      const next = new Set(multiple ? prev : []);
      if (prev.has(key)) {
        next.delete(key);
      } else {
        next.add(key);
      }
      return next;
    });
  };

  return (
    <div className={className} style={{ display: "flex", flexDirection: "column", ...style }}>
      {items.map((item) => {
        const isOpen = openKeys.has(item.key);
        return (
          <div
            key={item.key}
            style={{
              borderBottom: "1px solid var(--border-subtle)",
            }}
          >
            <button
              onClick={() => toggle(item.key)}
              aria-expanded={isOpen}
              style={{
                display: "flex",
                alignItems: "center",
                justifyContent: "space-between",
                width: "100%",
                padding: "14px 0",
                border: "none",
                background: "transparent",
                color: "var(--text-primary)",
                fontSize: 14,
                fontWeight: 500,
                cursor: "pointer",
                textAlign: "left",
              }}
            >
              <span>{item.title}</span>
              <span
                style={{
                  fontSize: 10,
                  color: "var(--text-muted)",
                  transition: "200ms ease-out",
                  transform: isOpen ? "rotate(180deg)" : "rotate(0)",
                }}
              >
                ▼
              </span>
            </button>
            <div
              style={{
                overflow: "hidden",
                maxHeight: isOpen ? 500 : 0,
                opacity: isOpen ? 1 : 0,
                transition: "300ms ease-in-out",
                paddingBottom: isOpen ? 14 : 0,
              }}
            >
              <div style={{ fontSize: 13, color: "var(--text-secondary)", lineHeight: 1.6 }}>
                {item.content}
              </div>
            </div>
          </div>
        );
      })}
    </div>
  );
}
