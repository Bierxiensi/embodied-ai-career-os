import type { SemanticTokens } from '../semantic';
import { colors } from '../primitives';

/** Ardot Light — 克制精致，Apple 风。 */
export const lightTheme: SemanticTokens = {
  surface: {
    canvas: '#F5F5F7',
    card: colors.white,
    elevated: colors.white,
    overlay: 'rgba(0, 0, 0, 0.4)',
    sidebar: '#FAFAFB',
  },

  text: {
    primary: '#1D1D1F',
    secondary: '#3A3A3C',
    muted: '#787880',
    inverse: colors.white,
    link: '#0066CC',
  },

  border: {
    default: '#E0E0E0',
    subtle: '#E8E8ED',
    focus: '#0066CC',
    error: colors.rose[500],
  },

  accent: {
    primary: '#0066CC',
    primaryHover: '#0055AA',
    primarySoft: '#EAF3FC',
    success: colors.emerald[500],
    successSoft: '#DDF4EA',
    warning: colors.amber[500],
    warningSoft: '#FEF3C7',
    danger: colors.rose[500],
    dangerSoft: '#FEF2F2',
  },

  shadow: {
    card: '0 1px 3px rgba(0, 0, 0, 0.06)',
    elevated: '0 4px 16px rgba(0, 0, 0, 0.12)',
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
