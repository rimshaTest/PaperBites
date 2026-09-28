import React, { useRef, useState } from 'react';
import { Modal, StyleSheet, Text, TouchableOpacity, View, Animated } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import * as Haptics from 'expo-haptics';
import { recordPaperView } from '../services/api';
import { useTheme } from '../hooks/useTheme';

/**
 * Libby-style "Did you read this paper?" prompt - but unlike the AppState-based approach this
 * replaced, it's triggered directly by the caller (paper/[id].js) right after
 * WebBrowser.openBrowserAsync() resolves, i.e. the moment the in-app browser showing the paper
 * closes and control returns to this screen. That's a deterministic signal (a resolved promise),
 * not a guess at an OS-level app-foreground transition - see paper/[id].js's handleOpenLink for
 * why that AppState approach was unreliable and got replaced.
 */
export default function ReadConfirmationModal({ visible, paper, token, onDismiss }) {
  const { theme } = useTheme();
  const styles = React.useMemo(() => createStyles(theme), [theme]);
  const [milestone, setMilestone] = useState(null);
  const badgeScale = useRef(new Animated.Value(0)).current;
  const badgeOpacity = useRef(new Animated.Value(0)).current;

  const playMilestoneAnimation = (badgeNumber) => {
    setMilestone(badgeNumber);
    badgeScale.setValue(0);
    badgeOpacity.setValue(1);
    Haptics.notificationAsync(Haptics.NotificationFeedbackType.Success).catch(() => {});
    Animated.sequence([
      Animated.spring(badgeScale, { toValue: 1, friction: 4, tension: 80, useNativeDriver: true }),
      Animated.delay(1000),
      Animated.timing(badgeOpacity, { toValue: 0, duration: 300, useNativeDriver: true }),
    ]).start(() => setMilestone(null));
  };

  const handleYes = async () => {
    Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Medium).catch(() => {});
    onDismiss();
    if (token && paper) {
      const result = await recordPaperView(token, paper.id);
      if (result && result.milestone_reached) {
        playMilestoneAnimation(result.milestone_reached);
      }
    }
  };

  const handleNo = () => {
    Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Light).catch(() => {});
    onDismiss();
  };

  return (
    <>
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

      {milestone && (
        <View style={styles.celebrationOverlay} pointerEvents="none">
          <Animated.View
            style={[
              styles.badge,
              { transform: [{ scale: badgeScale }], opacity: badgeOpacity },
            ]}
          >
            <Ionicons name="flame" size={56} color="#FFFFFF" />
            <Text style={styles.badgeNumber}>{milestone}</Text>
            <Text style={styles.badgeLabel}>papers read!</Text>
          </Animated.View>
        </View>
      )}
    </>
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
  celebrationOverlay: {
    ...StyleSheet.absoluteFillObject,
    alignItems: 'center',
    justifyContent: 'center',
  },
  badge: {
    backgroundColor: '#FF7A00',
    borderRadius: 100,
    width: 160,
    height: 160,
    alignItems: 'center',
    justifyContent: 'center',
    shadowColor: '#FF7A00',
    shadowOpacity: 0.6,
    shadowRadius: 20,
    elevation: 10,
  },
  badgeNumber: {
    fontSize: 32,
    fontWeight: '800',
    color: '#FFFFFF',
    marginTop: 4,
  },
  badgeLabel: {
    fontSize: 13,
    color: '#FFFFFF',
    fontWeight: '600',
  },
});
