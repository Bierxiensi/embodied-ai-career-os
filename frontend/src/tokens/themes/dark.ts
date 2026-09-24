import type { SemanticTokens } from '../semantic';
import { colors } from '../primitives';

/** Ardot Dark — 沉稳专业，Linear 风。 */
export const darkTheme: SemanticTokens = {
  surface: {
    canvas: '#0A0A0C',
    card: '#18181B',
    elevated: '#232326',
    overlay: 'rgba(0, 0, 0, 0.6)',
    sidebar: '#111113',
  },

  text: {
    primary: '#F5F5F7',
    secondary: '#D1D1D6',
    muted: '#9898A0',
    inverse: '#1D1D1F',
    link: '#60A5FA',
  },

  border: {
    default: '#38383A',
    subtle: '#2C2C2E',
    focus: '#3B82F6',
    error: colors.rose[500],
  },

  accent: {
    primary: '#3B82F6',
    primaryHover: '#60A5FA',
    primarySoft: 'rgba(59, 130, 246, 0.15)',
    success: colors.emerald[400],
    successSoft: 'rgba(52, 211, 153, 0.15)',
    warning: colors.amber[400],
    warningSoft: 'rgba(251, 191, 36, 0.15)',
    danger: colors.rose[400],
    dangerSoft: 'rgba(251, 113, 133, 0.15)',
  },

  shadow: {
    card: '0 0 0 1px rgba(255, 255, 255, 0.06)',
    elevated: '0 0 0 1px rgba(255, 255, 255, 0.08), 0 8px 24px rgba(0, 0, 0, 0.4)',
    glow: 'none',
  },

  gradient: {
    accent: 'none',
    subtle: 'none',
  },

  backdrop: {
    blur: 'none',
  },

  radius: {
    card: '16px',
    item: '10px',
  },
};
