import React, { useEffect, useMemo, useRef, useState } from 'react';
import { AppState, Modal, StyleSheet, Text, TouchableOpacity, View, Animated } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import * as Haptics from 'expo-haptics';
import { getPendingReadConfirmation, clearPendingReadConfirmation } from '../services/storage';
import { recordPaperView } from '../services/api';
import { useAuth } from '../hooks/useAuth';
import { useTheme } from '../hooks/useTheme';

/**
 * Libby-style "Did you read this paper?" prompt. Paper/[id]'s "View Original Paper" button only
 * stashes the paper as *pending* (services/storage.js); it's this gate, watching for the app
 * coming back to the foreground, that turns a pending paper into a confirmed read (or discards it
 * on "No") - confirmed reads are what count for the Visualize graph, per-topic stats, and
 * milestone badges. Lives at the root of the app (see _layout.tsx) so it can fire over any screen.
 */
export default function ReadConfirmationGate() {
  const { token } = useAuth();
  const { theme } = useTheme();
  const styles = useMemo(() => createStyles(theme), [theme]);
  const [pending, setPending] = useState(null);
  const [milestone, setMilestone] = useState(null);
  const appState = useRef(AppState.currentState);
  const badgeScale = useRef(new Animated.Value(0)).current;
  const badgeOpacity = useRef(new Animated.Value(0)).current;

  const checkPending = async () => {
    const paper = await getPendingReadConfirmation();
    if (paper) setPending(paper);
  };

  useEffect(() => {
    // Covers both "backgrounded then resumed" and "app was killed while a confirmation was
    // pending and just cold-started" - the latter needs a check on mount too, not just on the
    // AppState transition, since a killed app never fires 'change'.
    checkPending();

    const subscription = AppState.addEventListener('change', (nextState) => {
      if (appState.current.match(/inactive|background/) && nextState === 'active') {
        checkPending();
      }
      appState.current = nextState;
    });

    return () => subscription.remove();
  }, []);

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
    const paper = pending;
    setPending(null);
    await clearPendingReadConfirmation();
    if (token && paper) {
      const result = await recordPaperView(token, paper.id);
      if (result && result.milestone_reached) {
        playMilestoneAnimation(result.milestone_reached);
      }
    }
  };

  const handleNo = async () => {
    Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Light).catch(() => {});
    setPending(null);
    await clearPendingReadConfirmation();
  };

  return (
    <>
      <Modal visible={!!pending} transparent animationType="fade">
        <View style={styles.overlay}>
          <View style={styles.card}>
            <Text style={styles.title}>Did you read this paper?</Text>
            {pending?.title ? (
              <Text style={styles.subtitle} numberOfLines={2}>{pending.title}</Text>
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
