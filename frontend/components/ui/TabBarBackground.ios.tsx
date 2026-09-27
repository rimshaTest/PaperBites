import { useBottomTabBarHeight } from 'expo-router/js-tabs';
import { BlurView } from 'expo-blur';
import { StyleSheet } from 'react-native';
import { useTheme } from '../../hooks/useTheme';

export default function BlurTabBarBackground() {
  // Explicitly tinted by our own light/dark scheme rather than "systemChromeMaterial" (which
  // follows the OS's appearance) - the app's Settings screen lets someone pin light or dark
  // independent of their OS setting, and the tab bar needs to follow that choice too.
  const { scheme } = useTheme();
  return (
    <BlurView
      tint={scheme === 'dark' ? 'systemChromeMaterialDark' : 'systemChromeMaterialLight'}
      intensity={100}
      style={StyleSheet.absoluteFill}
    />
  );
}

export function useBottomTabOverflow() {
  return useBottomTabBarHeight();
}
