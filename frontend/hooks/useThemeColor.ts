/**
 * Resolves a color from the app theme (constants/theme.js via useTheme), unless the caller
 * passes an explicit light/dark override.
 */

import { useTheme } from './useTheme';

type ThemeColorName = 'background' | 'surface' | 'text' | 'textMuted' | 'border' | 'accent' | 'danger';

export function useThemeColor(
  props: { light?: string; dark?: string },
  colorName: ThemeColorName
) {
  const { theme, scheme } = useTheme();
  return props[scheme] ?? theme[colorName];
}
