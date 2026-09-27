import { Platform } from 'react-native';

const serif = Platform.select({ ios: 'Georgia', android: 'serif', default: 'Georgia, "Times New Roman", serif' });

// The original "paper" palette - now the light theme. Kept as named exports (rather than one
// object with nested light/dark keys) so every existing `theme.xxx` reference in already-written
// styles keeps working unchanged for whichever palette useTheme() resolves to.
export const lightTheme = {
  mode: 'light',
  background: '#f3f0e9',
  surface: '#FFFFFF',
  text: '#1A1A1A',
  textMuted: '#5e5e5e',
  border: '#1A1A1A',
  accent: '#cf9e2c',
  danger: '#E53935',
  serif,
};

export const darkTheme = {
  mode: 'dark',
  background: '#2a261e',
  surface: '#2a261e',
  text: '#EDEAE3',
  textMuted: '#ffe2a4',
  border: '#cbbda1',
  accent: '#a17919',
  danger: '#FF6B60',
  serif,
};

// Default export is the light palette, for any code that hasn't been switched over to
// useTheme() yet - keeps this a non-breaking change while the rollout is in progress.
export default lightTheme;
