import { Platform } from 'react-native';

// Shared design tokens for the "paper" theme (login, interests, profile, settings).
export const theme = {
  background: '#f3f0e9',
  surface: '#FFFFFF',
  text: '#1A1A1A',
  textMuted: '#6B6B6B',
  border: '#1A1A1A',
  accent: '#c5b590',
  danger: '#E53935',
  serif: Platform.select({ ios: 'Georgia', android: 'serif', default: 'Georgia, "Times New Roman", serif' }),
};

export default theme;
