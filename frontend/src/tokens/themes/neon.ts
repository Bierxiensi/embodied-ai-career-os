import type { SemanticTokens } from '../semantic';
import { colors } from '../primitives';

/** Ardot Neon — 品牌驱动，Stripe 风。深色基底 + 渐变强调 + 毛玻璃。 */
export const neonTheme: SemanticTokens = {
  surface: {
    canvas: '#0F0F14',
    card: 'rgba(255, 255, 255, 0.03)',
    elevated: 'rgba(255, 255, 255, 0.06)',
    overlay: 'rgba(0, 0, 0, 0.7)',
    sidebar: 'rgba(255, 255, 255, 0.02)',
  },

  text: {
    primary: '#F5F5F7',
    secondary: '#D1D1D6',
    muted: '#71717A',
    inverse: '#0F0F14',
    link: '#A78BFA',
  },

  border: {
    default: 'rgba(255, 255, 255, 0.08)',
    subtle: 'rgba(255, 255, 255, 0.04)',
    focus: colors.violet[500],
    error: colors.rose[500],
  },

  accent: {
    primary: colors.violet[500],
    primaryHover: colors.violet[400],
    primarySoft: 'rgba(139, 92, 246, 0.15)',
    success: colors.emerald[400],
    successSoft: 'rgba(52, 211, 153, 0.15)',
    warning: colors.amber[400],
    warningSoft: 'rgba(251, 191, 36, 0.15)',
    danger: colors.rose[400],
    dangerSoft: 'rgba(251, 113, 133, 0.15)',
  },

  shadow: {
    card: '0 0 0 1px rgba(255, 255, 255, 0.08), 0 4px 16px rgba(0, 0, 0, 0.3)',
    elevated: '0 0 0 1px rgba(255, 255, 255, 0.1), 0 8px 32px rgba(0, 0, 0, 0.5)',
    glow: '0 0 40px rgba(139, 92, 246, 0.15)',
  },

  gradient: {
    accent: 'linear-gradient(135deg, #8B5CF6, #3B82F6)',
    subtle: 'linear-gradient(180deg, rgba(139, 92, 246, 0.05) 0%, transparent 100%)',
  },

  backdrop: {
    blur: 'blur(12px)',
  },

  radius: {
    card: '20px',
    item: '12px',
  },
};
