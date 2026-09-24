"use client";

import { useState, useRef, useEffect } from 'react';
import { useTheme } from './useTheme';

export default function ThemeSwitcher() {
  const { theme, themes, setTheme } = useTheme();
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  const current = themes.find((t) => t.id === theme) ?? themes[0];

  // 点击外部关闭
  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) {
        setOpen(false);
      }
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, []);

  return (
    <div ref={ref} style={{ position: 'relative' }}>
      <button
        onClick={() => setOpen(!open)}
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: 6,
          padding: '6px 10px',
          borderRadius: 'var(--radius-item)',
          border: '1px solid var(--border-subtle)',
          background: 'var(--surface-card)',
          color: 'var(--text-secondary)',
          cursor: 'pointer',
          fontSize: 13,
          transition: '120ms ease-out',
        }}
        aria-label="切换主题"
      >
        <span>{current.icon}</span>
        <span>{current.label}</span>
      </button>

      {open && (
        <div
          style={{
            position: 'absolute',
            top: '100%',
            right: 0,
            marginTop: 4,
            minWidth: 140,
            background: 'var(--surface-elevated)',
            border: '1px solid var(--border-default)',
            borderRadius: 'var(--radius-item)',
            boxShadow: 'var(--shadow-elevated)',
            zIndex: 1000,
            overflow: 'hidden',
          }}
        >
          {themes.map((t) => (
            <button
              key={t.id}
              onClick={() => {
                setTheme(t.id);
                setOpen(false);
              }}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: 8,
                width: '100%',
                padding: '10px 14px',
                border: 'none',
                background: t.id === theme ? 'var(--accent-primary-soft)' : 'transparent',
                color: t.id === theme ? 'var(--accent-primary)' : 'var(--text-primary)',
                cursor: 'pointer',
                fontSize: 13,
                fontWeight: t.id === theme ? 600 : 400,
                transition: '120ms ease-out',
              }}
              onMouseEnter={(e) => {
                if (t.id !== theme) {
                  e.currentTarget.style.background = 'var(--surface-card)';
                }
              }}
              onMouseLeave={(e) => {
                if (t.id !== theme) {
                  e.currentTarget.style.background = 'transparent';
                }
              }}
            >
              <span>{t.icon}</span>
              <span>{t.label}</span>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
