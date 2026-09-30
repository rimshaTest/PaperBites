import React from 'react';
import { TouchableOpacity, StyleSheet } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import * as Haptics from 'expo-haptics';
import { useTheme } from '../hooks/useTheme';

/**
 * The center "+" tab bar button (Instagram-style) that opens the add-paper modal. Rendered as
 * the tabBarButton for a placeholder tab slot between Visualize and Saved (see (tabs)/_layout.tsx)
 * - that slot's own screen is never actually shown, since its tabPress listener always intercepts
 * the press and pushes /add-paper instead of switching to it.
 */
/**
 * @param {{ onPress?: (event: any) => void }} props
 */
export function AddPaperTabButton({ onPress } = {}) {
  const { theme } = useTheme();
  const styles = React.useMemo(() => createStyles(theme), [theme]);

  return (
    <TouchableOpacity
      style={styles.button}
      activeOpacity={0.85}
      onPress={(event) => {
        Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Medium).catch(() => {});
        onPress?.(event);
      }}
    >
      <Ionicons name="add" size={30} color={theme.text} />
    </TouchableOpacity>
  );
}

const createStyles = (theme) => StyleSheet.create({
  button: {
    marginTop: -24,
    alignSelf: 'center',
    width: 56,
    height: 56,
    borderRadius: 28,
    backgroundColor: theme.accent,
    borderWidth: 3,
    borderColor: theme.background,
    alignItems: 'center',
    justifyContent: 'center',
    shadowColor: '#000',
    shadowOpacity: 0.25,
    shadowRadius: 6,
    shadowOffset: { width: 0, height: 3 },
    elevation: 6,
  },
});
