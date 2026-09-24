"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState, type ReactNode } from "react";

interface SidebarItem {
  href: string;
  label: string;
  icon?: ReactNode;
  badge?: number;
}

interface SidebarSection {
  label: string;
  items: SidebarItem[];
}

interface SidebarProps {
  sections: SidebarSection[];
  collapsible?: boolean;
  defaultCollapsed?: boolean;
  header?: ReactNode;
  className?: string;
  style?: React.CSSProperties;
}

export default function Sidebar({
  sections,
  collapsible = true,
  defaultCollapsed = false,
  header,
  className,
  style,
}: SidebarProps) {
  const [collapsed, setCollapsed] = useState(defaultCollapsed);
  const pathname = usePathname();

  const isActive = (href: string) => {
    if (href === "/jobs" || href === "/plan") return pathname === href;
    return pathname.startsWith(href);
  };

  return (
    <aside
      className={className}
      style={{
        width: collapsed ? 64 : 240,
        minHeight: "100%",
        background: "var(--surface-sidebar)",
        borderRight: "1px solid var(--border-subtle)",
        display: "flex",
        flexDirection: "column",
        transition: "width 200ms ease-out",
        overflow: "hidden",
        flexShrink: 0,
        ...style,
      }}
    >
      {header && (
        <div style={{ padding: "16px 12px", borderBottom: "1px solid var(--border-subtle)" }}>
          {header}
        </div>
      )}

      <nav style={{ flex: 1, padding: "12px 8px", overflow: "auto" }}>
        {sections.map((section, si) => (
          <div key={si} style={{ marginBottom: 16 }}>
            {!collapsed && (
              <div
                style={{
                  fontSize: 11,
                  fontWeight: 600,
                  color: "var(--text-muted)",
                  textTransform: "uppercase",
                  letterSpacing: "0.04em",
                  padding: "4px 12px 8px",
                }}
              >
                {section.label}
              </div>
            )}
            {section.items.map((item) => {
              const active = isActive(item.href);
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  style={{
                    display: "flex",
                    alignItems: "center",
                    gap: 10,
                    padding: collapsed ? "10px 0" : "8px 12px",
                    justifyContent: collapsed ? "center" : "flex-start",
                    borderRadius: "var(--radius-item)",
                    background: active ? "var(--accent-primary-soft)" : "transparent",
                    color: active ? "var(--accent-primary)" : "var(--text-secondary)",
                    textDecoration: "none",
                    fontSize: 13,
                    fontWeight: active ? 600 : 400,
                    transition: "120ms ease-out",
                    marginBottom: 2,
                    position: "relative",
                  }}
                  title={collapsed ? item.label : undefined}
                >
                  {item.icon && (
                    <span style={{ display: "flex", alignItems: "center", fontSize: 16, flexShrink: 0 }}>
                      {item.icon}
                    </span>
                  )}
                  {!collapsed && <span style={{ flex: 1 }}>{item.label}</span>}
                  {!collapsed && item.badge != null && item.badge > 0 && (
                    <span
                      style={{
                        fontSize: 10,
                        fontWeight: 600,
                        padding: "2px 6px",
                        borderRadius: "var(--radius-pill)",
                        background: "var(--accent-danger)",
                        color: "var(--text-inverse)",
                      }}
                    >
                      {item.badge}
                    </span>
                  )}
                </Link>
              );
            })}
          </div>
        ))}
      </nav>

      {collapsible && (
        <button
          onClick={() => setCollapsed(!collapsed)}
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            padding: 12,
            border: "none",
            borderTop: "1px solid var(--border-subtle)",
            background: "transparent",
            color: "var(--text-muted)",
            cursor: "pointer",
            fontSize: 14,
            transition: "120ms ease-out",
          }}
          aria-label={collapsed ? "展开侧边栏" : "折叠侧边栏"}
        >
          {collapsed ? "→" : "←"}
        </button>
      )}
    </aside>
  );
}
