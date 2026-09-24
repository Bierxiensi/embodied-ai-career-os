"use client";

import Link from "next/link";
import type { ReactNode } from "react";

interface BreadcrumbItem {
  href?: string;
  label: string;
}

interface BreadcrumbProps {
  items: BreadcrumbItem[];
  separator?: ReactNode;
  className?: string;
  style?: React.CSSProperties;
}

export default function Breadcrumb({ items, separator = "/", className, style }: BreadcrumbProps) {
  return (
    <nav aria-label="面包屑" className={className} style={{ ...style }}>
      <ol
        style={{
          display: "flex",
          alignItems: "center",
          gap: 8,
          listStyle: "none",
          margin: 0,
          padding: 0,
          fontSize: 13,
        }}
      >
        {items.map((item, i) => {
          const isLast = i === items.length - 1;
          return (
            <li key={i} style={{ display: "flex", alignItems: "center", gap: 8 }}>
              {i > 0 && (
                <span style={{ color: "var(--text-muted)", fontSize: 11 }}>{separator}</span>
              )}
              {item.href && !isLast ? (
                <Link
                  href={item.href}
                  style={{
                    color: "var(--text-link)",
                    textDecoration: "none",
                    transition: "120ms ease-out",
                  }}
                >
                  {item.label}
                </Link>
              ) : (
                <span
                  style={{
                    color: isLast ? "var(--text-primary)" : "var(--text-muted)",
                    fontWeight: isLast ? 500 : 400,
                  }}
                >
                  {item.label}
                </span>
              )}
            </li>
          );
        })}
      </ol>
    </nav>
  );
}
