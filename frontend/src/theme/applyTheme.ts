import { themes, flattenTokens, type ThemeId } from '@/tokens';

/** 将主题 token 注入 <html> 的 data-theme 属性和 CSS 变量。 */
export function applyTheme(themeId: ThemeId): void {
  const root = document.documentElement;
  const theme = themes[themeId];
  if (!theme) return;

  // 设置 data-theme 属性
  root.setAttribute('data-theme', themeId);

  // 注入 CSS 变量
  const vars = flattenTokens(theme);
  for (const [key, value] of Object.entries(vars)) {
    root.style.setProperty(key, value);
  }

  // 存储偏好
  try {
    localStorage.setItem('ardot-theme', themeId);
  } catch {
    // localStorage 不可用时静默失败
  }
}

/** 从 localStorage 读取已保存的主题偏好。 */
export function getSavedTheme(): ThemeId {
  try {
    const saved = localStorage.getItem('ardot-theme');
    if (saved && saved in themes) return saved as ThemeId;
  } catch {
    // ignore
  }
  return 'ardot-light';
}

/** 生成指定主题的 CSS 变量字符串（用于 SSR 或 <style> 标签）。 */
export function getThemeCSS(themeId: ThemeId): string {
  const theme = themes[themeId];
  if (!theme) return '';

  const vars = flattenTokens(theme);
  const lines = Object.entries(vars).map(([key, value]) => `  ${key}: ${value};`);
  return `[data-theme="${themeId}"] {\n${lines.join('\n')}\n}`;
}
