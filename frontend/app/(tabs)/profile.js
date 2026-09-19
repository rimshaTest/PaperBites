import React from 'react';
import { View, Text, TouchableOpacity, StyleSheet, SafeAreaView } from 'react-native';
import { useRouter } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import { useAuth } from '../../hooks/useAuth';
import theme from '../../constants/theme';

export default function ProfileScreen() {
  const router = useRouter();
  const { user, loading, logout } = useAuth();

  const handleLogout = async () => {
    await logout();
  };

  return (
    <SafeAreaView style={styles.container}>
      <Text style={styles.headerTitle}>Profile</Text>

      {loading ? (
        <Text style={styles.infoText}>Loading...</Text>
      ) : user ? (
        <>
          <View style={styles.avatarSection}>
            <View style={styles.avatar}>
              <Ionicons name="person" size={40} color={theme.text} />
            </View>
            <Text style={styles.email}>{user.email}</Text>
          </View>

          <TouchableOpacity style={styles.row} onPress={() => router.push('/settings')}>
            <Ionicons name="settings-outline" size={22} color={theme.text} />
            <Text style={styles.rowText}>Settings</Text>
            <Ionicons name="chevron-forward" size={20} color={theme.textMuted} />
          </TouchableOpacity>

          <TouchableOpacity style={[styles.row, styles.logoutRow]} onPress={handleLogout}>
            <Ionicons name="log-out-outline" size={22} color={theme.danger} />
            <Text style={[styles.rowText, { color: theme.danger }]}>Log out</Text>
          </TouchableOpacity>
        </>
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
    color: theme.textMuted,
    marginBottom: 20,
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
  },
});
