import React, { useState, useCallback, useMemo } from 'react';
import { View, Text, TouchableOpacity, StyleSheet, ScrollView, Platform } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useRouter, useFocusEffect } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import { useAuth } from '../../hooks/useAuth';
import { useBottomTabBarHeight } from 'expo-router/js-tabs';
import { useTheme } from '../../hooks/useTheme';
import { fetchReadingStats } from '../../services/api';
import { MILESTONES } from '../../constants/milestones';

export default function ProfileScreen() {
  const router = useRouter();
  const { user, token, loading, logout } = useAuth();
  const { theme } = useTheme();
  const tabBarHeight = useBottomTabBarHeight();
  const bottomPadding = 48 + (Platform.OS === 'ios' ? tabBarHeight : 0);
  const styles = useMemo(() => createStyles(theme), [theme]);
  const [stats, setStats] = useState(null);

  // Reload every time the tab regains focus, same staleness fix as Saved/Visualize, so a
  // just-confirmed read's milestone/stats show up immediately after switching tabs.
  useFocusEffect(
    useCallback(() => {
      if (!token) {
        setStats(null);
        return;
      }
      let cancelled = false;
      fetchReadingStats(token).then((result) => {
        if (!cancelled) setStats(result);
      });
      return () => { cancelled = true; };
    }, [token])
  );

  const handleLogout = async () => {
    await logout();
  };

  const topCategories = stats
    ? Object.entries(stats.by_category).sort((a, b) => b[1] - a[1]).slice(0, 5)
    : [];

  return (
    <SafeAreaView style={styles.container} edges={['top']}>
      <ScrollView
        showsVerticalScrollIndicator={false}
        style={styles.scroll}
        contentContainerStyle={[styles.scrollContent, { paddingBottom: bottomPadding }]}
      >
      <Text style={styles.headerTitle}>Profile</Text>

      {loading ? (
        <Text style={styles.infoText}>Loading...</Text>
      ) : user ? (
        <View style={{ width: '100%' }}>
          <View style={styles.avatarSection}>
            <View style={styles.avatar}>
              <Ionicons name="person" size={40} color={theme.text} />
            </View>
            <Text style={styles.email}>{user.email + '  '}</Text>
          </View>

          {stats?.streak && (
            <View style={styles.streakTag}>
              <Ionicons name="flame" size={16} color={theme.accent} />
              <Text style={styles.streakTagText}>{stats.streak.label}</Text>
            </View>
          )}

          {stats && stats.total_read > 0 && (
            <View style={styles.statsCard}>
              <Text style={styles.statsHeading}>{stats.total_read} papers read</Text>

              <View style={styles.badgeRow}>
                {MILESTONES.map((m) => {
                  const earned = stats.milestones_reached.includes(m);
                  return (
                    <View key={m} style={styles.badgeItem}>
                      <View style={[styles.badgeCircle, earned && styles.badgeCircleEarned]}>
                        <Ionicons
                          name="flame"
                          size={20}
                          color={earned ? theme.onAccent : theme.textMuted}
                        />
                      </View>
                      <Text style={[styles.badgeCount, earned && styles.badgeCountEarned]}>{m}</Text>
                    </View>
                  );
                })}
              </View>

              {topCategories.length > 0 && (
                <View style={styles.categorySection}>
                  <Text style={styles.categoryHeading}>Your favorite topics</Text>
                  {topCategories.map(([category, count]) => (
                    <View key={category} style={styles.categoryRow}>
                      <View style={styles.categoryItem}>
                        <Text style={styles.categoryName}>{category}</Text>
                      </View>
                      <Text style={styles.categoryCount}>{count}</Text>
                    </View>
                  ))}
                </View>
              )}
            </View>
          )}

          <TouchableOpacity style={styles.row} onPress={() => router.push('/profile-details')}>
            <Ionicons name="person-circle-outline" size={22} color={theme.text} />
            <Text style={styles.rowText}>Profile Details</Text>
            <Ionicons name="chevron-forward" size={20} color={theme.textMuted} />
          </TouchableOpacity>

          <TouchableOpacity style={styles.row} onPress={() => router.push('/settings')}>
            <Ionicons name="settings-outline" size={22} color={theme.text} />
            <Text style={styles.rowText}>Settings</Text>
            <Ionicons name="chevron-forward" size={20} color={theme.textMuted} />
          </TouchableOpacity>

          <TouchableOpacity style={[styles.row, styles.logoutRow]} onPress={handleLogout}>
            <Ionicons name="log-out-outline" size={22} color={theme.text} />
            <Text style={[styles.rowText, { color: theme.text }]}>Log out</Text>
          </TouchableOpacity>
        </View>
      ) : (
        <View style={styles.avatarSection}>
          <View style={styles.avatar}>
            <Ionicons name="person" size={40} color={theme.textMuted} />
          </View>
          <Text style={styles.email}>Not signed in</Text>

          <TouchableOpacity style={styles.primaryButton} onPress={() => router.push('/login')}>
            <Text style={styles.primaryButtonText}>Log In</Text>
          </TouchableOpacity>
          <TouchableOpacity onPress={() => router.push('/signup')}>
            <Text style={styles.secondaryLink}>Sign Up</Text>
          </TouchableOpacity>
        </View>
      )}
      </ScrollView>
    </SafeAreaView>
  );
}

const createStyles = (theme) => StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: theme.background,
  },
  // The padding lives inside the scroll area (not on the screen container) so content scrolls
  // all the way to the tab bar instead of being clipped 20px above it. Spans the full width,
  // like the other tab screens.
  scroll: {
    flex: 1,
  },
  scrollContent: {
    padding: 20,
  },
  headerTitle: {
    fontFamily: theme.serif,
    fontSize: 28,
    fontWeight: 'bold',
    color: theme.text,
    marginBottom: 20,
  },
  infoText: {
    fontSize: 15,
    color: theme.textMuted,
  },
  avatarSection: {
    alignItems: 'center',
    marginBottom: 30,
  },
  avatar: {
    width: 80,
    height: 80,
    borderRadius: 40,
    borderWidth: 1.5,
    borderColor: theme.border,
    backgroundColor: theme.surface,
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: 10,
  },
  email: {
    fontSize: 15,
    lineHeight: 20,
    color: theme.textMuted,
    marginBottom: 20,
    paddingHorizontal: 24,
    textAlign: 'center',
  },
  primaryButton: {
    backgroundColor: theme.accent,
    borderWidth: 1.5,
    borderColor: theme.border,
    borderRadius: 10,
    paddingVertical: 12,
    paddingHorizontal: 40,
    marginBottom: 12,
  },
  primaryButtonText: {
    color: theme.text,
    fontSize: 16,
    fontWeight: 'bold',
  },
  secondaryLink: {
    color: theme.text,
    fontSize: 15,
    lineHeight: 20,
    textDecorationLine: 'underline',
  },
  row: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
    backgroundColor: theme.surface,
    borderWidth: 1.5,
    borderColor: theme.border,
    borderRadius: 10,
    paddingHorizontal: 16,
    paddingVertical: 14,
    marginBottom: 12,
  },
  rowText: {
    flex: 1,
    fontSize: 15,
    color: theme.text,
  },
  logoutRow: {
    marginTop: 20,
    borderColor: theme.danger,
    backgroundColor: theme.accent,
  },
  statsCard: {
    backgroundColor: theme.surface,
    borderWidth: 1.5,
    borderColor: theme.border,
    borderRadius: 10,
    padding: 16,
    marginBottom: 20,
  },
  statsHeading: {
    fontFamily: theme.serif,
    fontSize: 17,
    fontWeight: 'bold',
    color: theme.text,
    marginBottom: 12,
  },
  badgeRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
  },
  badgeItem: {
    alignItems: 'center',
  },
  badgeCircle: {
    width: 40,
    height: 40,
    borderRadius: 20,
    backgroundColor: theme.background,
    borderWidth: 1,
    borderColor: theme.border,
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: 4,
  },
  badgeCircleEarned: {
    backgroundColor: theme.streak,
    borderColor: theme.streak,
  },
  badgeCount: {
    fontSize: 11,
    color: theme.textMuted,
  },
  badgeCountEarned: {
    color: theme.text,
    fontWeight: '600',
  },
  categorySection: {
    marginTop: 16,
    paddingTop: 12,
    borderTopWidth: 1,
    borderTopColor: theme.background,
  },
  categoryHeading: {
    fontSize: 13,
    fontWeight: '600',
    color: theme.textMuted,
    marginBottom: 8,
    textTransform: 'uppercase',
  },
  categoryRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    paddingVertical: 4,
  },
  categoryItem: {
    width: '70%'
  },
  categoryName: {
    fontSize: 14,
    color: theme.text,
  },
  categoryCount: {
    fontSize: 14,
    color: theme.textMuted,
    fontWeight: '600',
  },
  streakTag: {
    flexDirection: 'row',
    alignItems: 'center',
    alignSelf: 'center',
    gap: 6,
    backgroundColor: theme.surface,
    borderWidth: 1.5,
    borderColor: theme.accent,
    borderRadius: 20,
    paddingHorizontal: 16,
    paddingVertical: 8,
    marginTop: -14,
    marginBottom: 20,
    shadowColor: theme.accent,
    shadowOpacity: 0.3,
    shadowRadius: 6,
    shadowOffset: { width: 0, height: 2 },
    elevation: 3,
  },
  streakTagText: {
    fontFamily: theme.serif,
    fontSize: 14,
    fontWeight: 'bold',
    color: theme.text,
  },
});
