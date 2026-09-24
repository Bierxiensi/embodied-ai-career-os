export { colors, spacing, radii, fontSizes, fontWeights, lineHeights, transitions } from './primitives';
export type { SemanticTokens } from './semantic';
export { flattenTokens } from './semantic';
export { lightTheme, darkTheme, neonTheme } from './themes';

import type { SemanticTokens } from './semantic';
import { lightTheme } from './themes/light';
import { darkTheme } from './themes/dark';
import { neonTheme } from './themes/neon';

export type ThemeId = 'ardot-light' | 'ardot-dark' | 'ardot-neon';

export const themes: Record<ThemeId, SemanticTokens> = {
  'ardot-light': lightTheme,
  'ardot-dark': darkTheme,
  'ardot-neon': neonTheme,
};

export const THEME_LIST: Array<{ id: ThemeId; label: string; icon: string }> = [
  { id: 'ardot-light', label: 'Light', icon: '☀️' },
  { id: 'ardot-dark', label: 'Dark', icon: '🌙' },
  { id: 'ardot-neon', label: 'Neon', icon: '⚡' },
];

export const DEFAULT_THEME: ThemeId = 'ardot-light';
