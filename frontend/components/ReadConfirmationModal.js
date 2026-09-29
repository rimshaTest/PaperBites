import React from 'react';
import { Modal, StyleSheet, Text, TouchableOpacity, View } from 'react-native';
import * as Haptics from 'expo-haptics';
import { useConfirmRead } from '../hooks/useConfirmRead';
import { useTheme } from '../hooks/useTheme';

/**
 * Libby-style "Did you read this paper?" prompt - but unlike the AppState-based approach this
 * replaced, it's triggered directly by the caller (paper/[id].js) right after
 * WebBrowser.openBrowserAsync() resolves, i.e. the moment the in-app browser showing the paper
 * closes and control returns to this screen. That's a deterministic signal (a resolved promise),
 * not a guess at an OS-level app-foreground transition - see paper/[id].js's handleOpenLink for
 * why that AppState approach was unreliable and got replaced.
 *
 * Any earned milestone celebration is shown by the app-wide <AchievementOverlay/> (see
 * hooks/useConfirmRead.js), not locally here - the same "I've Read This!" confirmation path is
 * also reachable directly from a paper card, so the celebration can't live only in this modal.
 */
export default function ReadConfirmationModal({ visible, paper, token, onDismiss }) {
  const { theme } = useTheme();
  const styles = React.useMemo(() => createStyles(theme), [theme]);
  const confirmRead = useConfirmRead();

  const handleYes = async () => {
    Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Medium).catch(() => {});
    onDismiss();
    if (token && paper) {
      await confirmRead(token, paper.id);
    }
  };

  const handleNo = () => {
    Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Light).catch(() => {});
    onDismiss();
  };

  return (
    <Modal visible={visible} transparent animationType="fade">
      <View style={styles.overlay}>
        <View style={styles.card}>
          <Text style={styles.title}>Did you read this paper?</Text>
          {paper?.title ? (
            <Text style={styles.subtitle} numberOfLines={2}>{paper.title}</Text>
          ) : null}
          <View style={styles.buttonRow}>
            <TouchableOpacity style={[styles.button, styles.noButton]} onPress={handleNo}>
              <Text style={styles.noButtonText}>No</Text>
            </TouchableOpacity>
            <TouchableOpacity style={[styles.button, styles.yesButton]} onPress={handleYes}>
              <Text style={styles.yesButtonText}>Yes</Text>
            </TouchableOpacity>
          </View>
        </View>
      </View>
    </Modal>
  );
}

const createStyles = (theme) => StyleSheet.create({
  overlay: {
    flex: 1,
    backgroundColor: 'rgba(0,0,0,0.5)',
    alignItems: 'center',
    justifyContent: 'center',
    padding: 24,
  },
  card: {
    width: '100%',
    maxWidth: 340,
    backgroundColor: theme.surface,
    borderRadius: 16,
    padding: 24,
    alignItems: 'center',
  },
  title: {
    fontSize: 18,
    fontFamily: theme.serif,
    fontWeight: '600',
    color: theme.text,
    marginBottom: 8,
    textAlign: 'center',
  },
  subtitle: {
    fontSize: 14,
    color: theme.textMuted,
    marginBottom: 20,
    textAlign: 'center',
  },
  buttonRow: {
    flexDirection: 'row',
    gap: 12,
    width: '100%',
  },
  button: {
    flex: 1,
    paddingVertical: 12,
    borderRadius: 10,
    alignItems: 'center',
  },
  noButton: {
    backgroundColor: theme.background,
    borderWidth: 1,
    borderColor: theme.border,
  },
  yesButton: {
    backgroundColor: theme.accent,
  },
  noButtonText: {
    color: theme.text,
    fontWeight: '600',
  },
  yesButtonText: {
    color: theme.text,
    fontWeight: '600',
  },
});
