import * as React from 'react';
import { View, Text, TouchableOpacity, StyleSheet } from 'react-native';
import {SafeAreaView} from 'react-native-safe-area-context';
import { useRouter, useFocusEffect } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import { getAuth, clearAuth } from '../../services/storage';
import theme from '../../constants/theme';

export default function ProfileScreen() {
  const router = useRouter();
  const [email, setEmail] = React.useState<string | null>(null);

  useFocusEffect(
    React.useCallback(() => {
      getAuth().then((session) => setEmail(session?.email ?? null));
    }, [])
  );

  const handleLogout = async () => {
    await clearAuth();
    router.replace('/login');
  };

  return (
    <SafeAreaView style={styles.container}>
      <Text style={styles.headerTitle}>Profile</Text>

      <View style={styles.avatarSection}>
        <View style={styles.avatar}>
          <Ionicons name="person" size={40} color={theme.text} />
        </View>
        <Text style={styles.email}>{email ?? 'Not signed in'}</Text>
      </View>

      <TouchableOpacity style={styles.row} onPress={() => router.push('/settings')}>
        <Ionicons name="settings-outline" size={22} color={theme.text} />
        <Text style={styles.rowText}>Settings</Text>
        <Ionicons name="chevron-forward" size={20} color="#999" />
      </TouchableOpacity>

      <TouchableOpacity style={[styles.row, styles.logoutRow]} onPress={handleLogout}>
        <Ionicons name="log-out-outline" size={22} color={theme.danger} />
        <Text style={[styles.rowText, { color: theme.danger }]}>Log out</Text>
      </TouchableOpacity>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: theme.background,
    padding: 20,
  },
  headerTitle: {
    fontFamily: theme.serif,
    fontSize: 28,
    fontWeight: 'bold',
    color: theme.text,
    marginBottom: 20,
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
    color: theme.textMuted,
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
  },
});
