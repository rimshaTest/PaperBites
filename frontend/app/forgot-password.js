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
import { useRouter } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import * as authApi from '../services/auth';
import { useTheme } from '../hooks/useTheme';

export default function ForgotPasswordScreen() {
  const router = useRouter();
  const { theme } = useTheme();
  const styles = useMemo(() => createStyles(theme), [theme]);
  const [email, setEmail] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [formError, setFormError] = useState(null);

  const handleSubmit = async () => {
    setFormError(null);
    if (!email.trim()) {
      setFormError('Enter your email');
      return;
    }

    setSubmitting(true);
    try {
      await authApi.forgotPassword(email.trim());
      router.push({ pathname: '/reset-password', params: { email: email.trim() } });
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
          <Text style={styles.headerTitle}>Reset Password</Text>
          <View style={styles.headerButton} />
        </View>

        <View style={styles.form}>
          <Text style={styles.description}>
            Enter your account email and we'll send you a code to reset your password.
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

          {formError && <Text style={styles.error}>{formError}</Text>}

          <TouchableOpacity
            style={[styles.submitButton, submitting && styles.submitButtonDisabled]}
            onPress={handleSubmit}
            disabled={submitting}
          >
            <Text style={styles.submitButtonText}>{submitting ? 'Sending...' : 'Send Code'}</Text>
          </TouchableOpacity>
        </View>
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
