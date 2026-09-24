"use client";

import { createContext, useEffect, useState, type ReactNode } from 'react';
import { applyTheme, getSavedTheme } from './applyTheme';
import { THEME_LIST, type ThemeId } from '@/tokens';

interface ThemeContextValue {
  theme: ThemeId;
  setTheme: (id: ThemeId) => void;
  themes: typeof THEME_LIST;
}

export const ThemeContext = createContext<ThemeContextValue>({
  theme: 'ardot-light',
  setTheme: () => {},
  themes: THEME_LIST,
});

export function ThemeProvider({ children }: { children: ReactNode }) {
  const [theme, setThemeState] = useState<ThemeId>('ardot-light');

  // 首次挂载：从 localStorage 恢复主题
  useEffect(() => {
    const saved = getSavedTheme();
    setThemeState(saved);
    applyTheme(saved);
  }, []);

  const setTheme = (id: ThemeId) => {
    setThemeState(id);
    applyTheme(id);
  };

  return (
    <ThemeContext.Provider value={{ theme, setTheme, themes: THEME_LIST }}>
      {children}
    </ThemeContext.Provider>
  );
}
