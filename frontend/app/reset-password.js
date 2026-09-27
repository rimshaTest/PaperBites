import React, { useState, useMemo } from 'react';
import {
  View,
  Text,
  TextInput,
  TouchableOpacity,
  StyleSheet,
  KeyboardAvoidingView,
  Platform,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useRouter, useLocalSearchParams } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import * as authApi from '../services/auth';
import { useTheme } from '../hooks/useTheme';

export default function ResetPasswordScreen() {
  const router = useRouter();
  const { email: emailParam } = useLocalSearchParams();
  const { theme } = useTheme();
  const styles = useMemo(() => createStyles(theme), [theme]);
  const [email, setEmail] = useState(emailParam || '');
  const [code, setCode] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [formError, setFormError] = useState(null);
  const [success, setSuccess] = useState(false);

  const handleSubmit = async () => {
    setFormError(null);
    if (!email.trim() || !code.trim() || !newPassword) {
      setFormError('Fill in every field');
      return;
    }
    if (newPassword.length < 8) {
      setFormError('Password must be at least 8 characters');
      return;
    }

    setSubmitting(true);
    try {
      await authApi.resetPassword(email.trim(), code.trim(), newPassword);
      setSuccess(true);
    } catch (err) {
      setFormError(err.message || 'Something went wrong');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <SafeAreaView style={styles.container}>
      <KeyboardAvoidingView
        behavior={Platform.OS === 'ios' ? 'padding' : undefined}
        style={styles.flex}
      >
        <View style={styles.header}>
          <TouchableOpacity onPress={() => router.back()} style={styles.headerButton}>
            <Ionicons name="arrow-back" size={24} color={theme.text} />
          </TouchableOpacity>
          <Text style={styles.headerTitle}>Enter Code</Text>
          <View style={styles.headerButton} />
        </View>

        {success ? (
          <View style={styles.form}>
            <Text style={styles.description}>
              Your password has been reset. Log in with your new password.
            </Text>
            <TouchableOpacity style={styles.submitButton} onPress={() => router.replace('/login')}>
              <Text style={styles.submitButtonText}>Go to Log In</Text>
            </TouchableOpacity>
          </View>
        ) : (
          <View style={styles.form}>
            <Text style={styles.description}>
              Enter the 6-digit code we emailed you, along with your new password.
            </Text>

            <TextInput
              style={styles.input}
              placeholder="Email"
              placeholderTextColor={theme.textMuted}
              value={email}
              onChangeText={setEmail}
              autoCapitalize="none"
              keyboardType="email-address"
            />
            <TextInput
              style={styles.input}
              placeholder="6-digit code"
              placeholderTextColor={theme.textMuted}
              value={code}
              onChangeText={setCode}
              keyboardType="number-pad"
              maxLength={6}
            />
            <TextInput
              style={styles.input}
              placeholder="New password (min. 8 characters)"
              placeholderTextColor={theme.textMuted}
              value={newPassword}
              onChangeText={setNewPassword}
              secureTextEntry
            />

            {formError && <Text style={styles.error}>{formError}</Text>}

            <TouchableOpacity
              style={[styles.submitButton, submitting && styles.submitButtonDisabled]}
              onPress={handleSubmit}
              disabled={submitting}
            >
              <Text style={styles.submitButtonText}>{submitting ? 'Resetting...' : 'Reset Password'}</Text>
            </TouchableOpacity>
          </View>
        )}
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}

const createStyles = (theme) => StyleSheet.create({
  container: { flex: 1, backgroundColor: theme.background },
  flex: { flex: 1 },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingHorizontal: 10,
    paddingVertical: 10,
    borderBottomWidth: 1,
    borderBottomColor: theme.border,
    backgroundColor: theme.surface,
  },
  headerButton: { width: 34, padding: 5 },
  headerTitle: { fontSize: 18, fontWeight: 'bold', color: theme.text },
  form: { padding: 20 },
  description: {
    fontSize: 14,
    color: theme.textMuted,
    marginBottom: 20,
    lineHeight: 20,
  },
  input: {
    borderWidth: 1,
    borderColor: theme.border,
    borderRadius: 8,
    paddingHorizontal: 14,
    paddingVertical: 12,
    fontSize: 16,
    marginBottom: 14,
    color: theme.text,
    backgroundColor: theme.surface,
  },
  error: {
    color: theme.danger,
    marginBottom: 14,
    fontSize: 14,
  },
  submitButton: {
    backgroundColor: theme.accent,
    alignItems: 'center',
    borderWidth: 1.5,
    borderColor: theme.border,
    borderRadius: 10,
    paddingVertical: 10,
    paddingHorizontal: 30,
    marginTop: 16,
  },
  submitButtonText: {
    color: theme.text,
    fontSize: 15,
    fontWeight: 'bold',
  },
  submitButtonDisabled: { opacity: 0.6 },
});
