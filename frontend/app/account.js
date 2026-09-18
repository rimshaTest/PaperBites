import React from 'react';
import { View, Text, TouchableOpacity, StyleSheet, SafeAreaView } from 'react-native';
import { useRouter } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import { useAuth } from '../hooks/useAuth';

export default function AccountScreen() {
  const router = useRouter();
  const { user, loading, logout } = useAuth();

  const handleLogout = async () => {
    await logout();
  };

  return (
    <SafeAreaView style={styles.container}>
      <View style={styles.header}>
        <TouchableOpacity onPress={() => router.back()} style={styles.headerButton}>
          <Ionicons name="arrow-back" size={24} color="#333" />
        </TouchableOpacity>
        <Text style={styles.headerTitle}>Account</Text>
        <View style={styles.headerButton} />
      </View>

      <View style={styles.content}>
        {loading ? (
          <Text style={styles.infoText}>Loading...</Text>
        ) : user ? (
          <>
            <Ionicons name="person-circle-outline" size={64} color="#4285F4" />
            <Text style={styles.email}>{user.email}</Text>
            <TouchableOpacity style={styles.logoutButton} onPress={handleLogout}>
              <Text style={styles.logoutButtonText}>Log Out</Text>
            </TouchableOpacity>
          </>
        ) : (
          <>
            <Ionicons name="person-circle-outline" size={64} color="#ccc" />
            <Text style={styles.infoText}>You're not signed in.</Text>
            <TouchableOpacity style={styles.primaryButton} onPress={() => router.push('/login')}>
              <Text style={styles.primaryButtonText}>Log In</Text>
            </TouchableOpacity>
            <TouchableOpacity style={styles.secondaryButton} onPress={() => router.push('/signup')}>
              <Text style={styles.secondaryButtonText}>Sign Up</Text>
            </TouchableOpacity>
          </>
        )}
      </View>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#fff' },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingHorizontal: 10,
    paddingVertical: 10,
    borderBottomWidth: 1,
    borderBottomColor: '#e0e0e0',
  },
  headerButton: { width: 34, padding: 5 },
  headerTitle: { fontSize: 18, fontWeight: 'bold', color: '#333' },
  content: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    padding: 30,
  },
  infoText: {
    fontSize: 15,
    color: '#666',
    marginTop: 12,
    marginBottom: 20,
    textAlign: 'center',
  },
  email: {
    fontSize: 18,
    fontWeight: 'bold',
    color: '#333',
    marginTop: 12,
    marginBottom: 24,
  },
  primaryButton: {
    backgroundColor: '#4285F4',
    borderRadius: 8,
    paddingVertical: 12,
    paddingHorizontal: 40,
    marginBottom: 12,
  },
  primaryButtonText: { color: '#fff', fontSize: 16, fontWeight: 'bold' },
  secondaryButton: {
    paddingVertical: 12,
    paddingHorizontal: 40,
  },
  secondaryButtonText: { color: '#4285F4', fontSize: 16 },
  logoutButton: {
    borderWidth: 1,
    borderColor: '#E53935',
    borderRadius: 8,
    paddingVertical: 12,
    paddingHorizontal: 40,
  },
  logoutButtonText: { color: '#E53935', fontSize: 16, fontWeight: 'bold' },
});
