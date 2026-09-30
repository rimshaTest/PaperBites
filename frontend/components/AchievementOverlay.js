import React, { useEffect, useRef } from 'react';
import { StyleSheet, Text, View, Animated, Easing } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import * as Haptics from 'expo-haptics';
import { useAudioPlayer } from 'expo-audio';
import { useAchievements } from '../hooks/useAchievements';
import { useTheme } from '../hooks/useTheme';
import { playWhenReady } from '../utils/sound';

const DING_SOUND = require('../assets/sounds/bookmark-ding.wav');

const ORDINAL_SUFFIXES = { 1: 'st', 2: 'nd', 3: 'rd' };
const ordinal = (n) => {
  const mod100 = n % 100;
  if (mod100 >= 11 && mod100 <= 13) return `${n}th`;
  return `${n}${ORDINAL_SUFFIXES[n % 10] || 'th'}`;
};
const milestoneTitle = (n) => (n === 1 ? 'Your first read!' : `Your ${ordinal(n)} read!`);

// A handful of sparkles at fixed offsets around the badge, each fading/twinkling on its own
// slight delay - cheap enough (a handful of Animated.Views) to feel glittery without pulling in
// a particle/confetti library for one popup.
const SPARKLES = [
  { top: -18, left: 10, delay: 0 },
  { top: 6, left: -26, delay: 90 },
  { top: 30, left: 96, delay: 150 },
  { top: -10, left: 108, delay: 60 },
  { top: 78, left: -18, delay: 200 },
  { top: 96, left: 88, delay: 40 },
];

export default function AchievementOverlay() {
  const { theme } = useTheme();
  const styles = React.useMemo(() => createStyles(theme), [theme]);
  const { milestone, dismiss } = useAchievements();
  const ding = useAudioPlayer(DING_SOUND);

  const scale = useRef(new Animated.Value(0)).current;
  const opacity = useRef(new Animated.Value(0)).current;
  const sparkleAnims = useRef(SPARKLES.map(() => new Animated.Value(0))).current;

  useEffect(() => {
    if (!milestone) return;

    Haptics.notificationAsync(Haptics.NotificationFeedbackType.Success).catch(() => {});
    try {
      playWhenReady(ding);
    } catch (err) {
      console.debug('Achievement ding failed to play:', err);
    }

    scale.setValue(0);
    opacity.setValue(1);
    sparkleAnims.forEach((anim) => anim.setValue(0));

    const sparkleAnimations = sparkleAnims.map((anim, index) =>
      Animated.sequence([
        Animated.delay(SPARKLES[index].delay),
        Animated.timing(anim, { toValue: 1, duration: 260, easing: Easing.out(Easing.quad), useNativeDriver: true }),
        Animated.timing(anim, { toValue: 0, duration: 400, delay: 300, useNativeDriver: true }),
      ])
    );

    Animated.sequence([
      Animated.spring(scale, { toValue: 1, friction: 4, tension: 80, useNativeDriver: true }),
      Animated.delay(1400),
      Animated.timing(opacity, { toValue: 0, duration: 300, useNativeDriver: true }),
    ]).start(dismiss);
    Animated.parallel(sparkleAnimations).start();
  }, [milestone]);

  if (!milestone) return null;

  return (
    <View style={styles.overlay} pointerEvents="none">
      <Animated.View style={[styles.badgeWrap, { transform: [{ scale }], opacity }]}>
        {SPARKLES.map((sparkle, index) => (
          <Animated.View
            key={index}
            style={[
              styles.sparkle,
              {
                top: sparkle.top,
                left: sparkle.left,
                opacity: sparkleAnims[index],
                transform: [
                  { scale: sparkleAnims[index] },
                  {
                    rotate: sparkleAnims[index].interpolate({
                      inputRange: [0, 1],
                      outputRange: ['0deg', '90deg'],
                    }),
                  },
                ],
              },
            ]}
          >
            <Ionicons name="sparkles" size={18} color={theme.onAccent} />
          </Animated.View>
        ))}
        <View style={styles.badge}>
          <Ionicons name="flame" size={44} color={theme.onAccent} />
          <Text style={styles.badgeNumber}>{milestone}</Text>
        </View>
        <Text style={styles.badgeTitle}>{milestoneTitle(milestone)}</Text>
      </Animated.View>
    </View>
  );
}

const createStyles = (theme) => StyleSheet.create({
  overlay: {
    ...StyleSheet.absoluteFillObject,
    alignItems: 'center',
    justifyContent: 'center',
    zIndex: 999,
    elevation: 999,
  },
  badgeWrap: {
    alignItems: 'center',
  },
  badge: {
    backgroundColor: theme.streak,
    borderRadius: 100,
    width: 140,
    height: 140,
    alignItems: 'center',
    justifyContent: 'center',
    shadowColor: theme.streak,
    shadowOpacity: 0.7,
    shadowRadius: 24,
    elevation: 12,
  },
  badgeNumber: {
    fontSize: 28,
    fontWeight: '800',
    color: theme.onAccent,
    marginTop: 2,
  },
  badgeTitle: {
    marginTop: 14,
    fontFamily: theme.serif,
    fontSize: 18,
    fontWeight: 'bold',
    color: theme.text,
    backgroundColor: theme.surface,
    paddingHorizontal: 16,
    paddingVertical: 8,
    borderRadius: 20,
    overflow: 'hidden',
    textAlign: 'center',
  },
  sparkle: {
    position: 'absolute',
  },
});
