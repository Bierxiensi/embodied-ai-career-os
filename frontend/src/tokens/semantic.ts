/** Layer 2: Semantic Token 类型定义 — 主题切换层。 */

export interface SemanticTokens {
  // 表面（背景）
  surface: {
    canvas: string;
    card: string;
    elevated: string;
    overlay: string;
    sidebar: string;
  };

  // 文本
  text: {
    primary: string;
    secondary: string;
    muted: string;
    inverse: string;
    link: string;
  };

  // 边框
  border: {
    default: string;
    subtle: string;
    focus: string;
    error: string;
  };

  // 强调色
  accent: {
    primary: string;
    primaryHover: string;
    primarySoft: string;
    success: string;
    successSoft: string;
    warning: string;
    warningSoft: string;
    danger: string;
    dangerSoft: string;
  };

  // 阴影
  shadow: {
    card: string;
    elevated: string;
    glow: string;
  };

  // 渐变（Neon 主题专属，其他主题为空字符串）
  gradient: {
    accent: string;
    subtle: string;
  };

  // 毛玻璃（Neon 主题专属，其他主题为 'none'）
  backdrop: {
    blur: string;
  };

  // 圆角覆盖（Neon 主题更大）
  radius: {
    card: string;
    item: string;
  };
}

/** 将 SemanticTokens 扁平化为 CSS 变量键值对。 */
export function flattenTokens(tokens: SemanticTokens): Record<string, string> {
  const result: Record<string, string> = {};

  for (const [group, values] of Object.entries(tokens)) {
    for (const [key, value] of Object.entries(values as Record<string, string>)) {
      // surface.canvas → --surface-canvas
      const cssKey = `--${group}-${key.replace(/([A-Z])/g, '-$1').toLowerCase()}`;
      result[cssKey] = value;
    }
  }

  return result;
}
