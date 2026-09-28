import { Platform } from 'react-native';

const serif = Platform.select({ ios: 'Georgia', android: 'serif', default: 'Georgia, "Times New Roman", serif' });

// The original "paper" palette - now the light theme. Kept as named exports (rather than one
// object with nested light/dark keys) so every existing `theme.xxx` reference in already-written
// styles keeps working unchanged for whichever palette useTheme() resolves to.
export const lightTheme = {
  mode: 'light',
  background: '#f4f9f9',
  surface: '#addedc',
  text: '#1A1A1A',
  textMuted: '#898989',
  border: '#1A1A1A',
  accent: '#5cafac',
  danger: '#9b0c09',
  serif,
};

export const darkTheme = {
  mode: 'dark',
  background: '#1e292a',
  surface: '#106663',
  text: '#dae8e8',
  textMuted: '#b3cfcf',
  border: '#6c8b8a',
  accent: '#5cafac',
  danger: '#9b0c09',
  serif,
};

// Default export is the light palette, for any code that hasn't been switched over to
// useTheme() yet - keeps this a non-breaking change while the rollout is in progress.
export default lightTheme;
