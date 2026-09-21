import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  TextInput,
  TouchableOpacity,
  StyleSheet,
  ScrollView,
  ActivityIndicator,
  SafeAreaView,
} from 'react-native';
import { useRouter } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import { fetchProfile, saveProfileTier1, saveProfileTier2 } from '../services/api';
import { useAuth } from '../hooks/useAuth';
import theme from '../constants/theme';

const TIER2_FIELDS = [
  { key: 'age', label: 'Age' },
  { key: 'gender', label: 'Gender' },
  { key: 'sex', label: 'Sex' },
  { key: 'location_precise', label: 'Precise location' },
  { key: 'mental_disabilities', label: 'Mental disabilities' },
  { key: 'physical_disabilities', label: 'Physical disabilities' },
  { key: 'chronic_illnesses', label: 'Chronic illnesses' },
];

export default function ProfileDetailsScreen() {
  const router = useRouter();
  const { user, token, loading: authLoading } = useAuth();

  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);

  const [tier1, setTier1] = useState({
    field_of_study: '',
    education_level: '',
    general_interests: '',
    location: '',
  });
  const [tier2Fields, setTier2Fields] = useState({});
  const [tier2Consent, setTier2Consent] = useState({});

  useEffect(() => {
    if (!token) {
      setLoading(false);
      return;
    }

    const load = async () => {
      try {
        setLoading(true);
        const profile = await fetchProfile(token);
        setTier1((prev) => ({ ...prev, ...(profile.tier1 || {}) }));
        setTier2Fields(profile.tier2?.fields || {});
        setTier2Consent(profile.tier2?.consent || {});
      } catch (err) {
        console.error('Failed to load profile:', err);
      } finally {
        setLoading(false);
      }
    };
    load();
  }, [token]);

  const updateTier1 = (key, value) => {
    setSaved(false);
    setTier1((prev) => ({ ...prev, [key]: value }));
  };

  const updateTier2Field = (key, value) => {
    setSaved(false);
    setTier2Fields((prev) => ({ ...prev, [key]: value }));
  };

  const toggleConsent = (key, flag) => {
    setSaved(false);
    setTier2Consent((prev) => ({
      ...prev,
      [key]: {
        used_for_personalization: prev[key]?.used_for_personalization || false,
        used_for_feed_relevance: prev[key]?.used_for_feed_relevance || false,
        [flag]: !prev[key]?.[flag],
      },
    }));
  };

  const handleSave = async () => {
    if (!token) return;
    setSaving(true);
    try {
      await saveProfileTier1(token, tier1);
      // Only send Tier 2 fields that actually have a value, so clearing a field doesn't
      // re-save it as an empty string every time.
      const nonEmptyTier2Fields = Object.fromEntries(
        Object.entries(tier2Fields).filter(([, value]) => value !== '' && value != null)
      );
      await saveProfileTier2(token, nonEmptyTier2Fields, tier2Consent);
      setSaved(true);
    } catch (err) {
      console.error('Failed to save profile:', err);
    } finally {
      setSaving(false);
    }
  };

  if (authLoading || (loading && token)) {
    return (
      <SafeAreaView style={styles.container}>
        <ActivityIndicator style={{ marginTop: 40 }} size="large" color={theme.text} />
      </SafeAreaView>
    );
  }

  if (!user) {
    return (
      <SafeAreaView style={styles.container}>
        <View style={styles.header}>
          <TouchableOpacity onPress={() => router.back()} style={styles.headerButton}>
            <Ionicons name="arrow-back" size={24} color={theme.text} />
          </TouchableOpacity>
          <Text style={styles.headerTitle}>Profile Details</Text>
          <View style={styles.headerButton} />
        </View>
        <View style={styles.centerContainer}>
          <Ionicons name="lock-closed-outline" size={40} color={theme.textMuted} />
          <Text style={styles.emptyText}>Log in to fill out your profile.</Text>
          <TouchableOpacity style={styles.loginButton} onPress={() => router.push('/login')}>
            <Text style={styles.loginButtonText}>Log In</Text>
          </TouchableOpacity>
        </View>
      </SafeAreaView>
    );
  }

  return (
    <SafeAreaView style={styles.container}>
      <View style={styles.header}>
        <TouchableOpacity onPress={() => router.back()} style={styles.headerButton}>
          <Ionicons name="arrow-back" size={24} color={theme.text} />
        </TouchableOpacity>
        <Text style={styles.headerTitle}>Profile Details</Text>
        <View style={styles.headerButton} />
      </View>

      <ScrollView contentContainerStyle={styles.content}>
        <Text style={styles.disclaimer}>
          Everything below is optional. It's used only to make your feed and reading experience
          more relevant, and is kept anonymized - never shared or shown to other users.
        </Text>

        <Text style={styles.sectionTitle}>About you</Text>
        <View style={styles.field}>
          <Text style={styles.label}>Field of study</Text>
          <TextInput
            style={styles.input}
            value={tier1.field_of_study}
            onChangeText={(v) => updateTier1('field_of_study', v)}
            placeholder="e.g. Neuroscience"
            placeholderTextColor={theme.textMuted}
          />
        </View>
        <View style={styles.field}>
          <Text style={styles.label}>Education level</Text>
          <TextInput
            style={styles.input}
            value={tier1.education_level}
            onChangeText={(v) => updateTier1('education_level', v)}
            placeholder="e.g. Undergraduate"
            placeholderTextColor={theme.textMuted}
          />
        </View>
        <View style={styles.field}>
          <Text style={styles.label}>General interests</Text>
          <TextInput
            style={styles.input}
            value={tier1.general_interests}
            onChangeText={(v) => updateTier1('general_interests', v)}
            placeholder="e.g. climate policy, genetics"
            placeholderTextColor={theme.textMuted}
          />
        </View>
        <View style={styles.field}>
          <Text style={styles.label}>Location (country/region)</Text>
          <TextInput
            style={styles.input}
            value={tier1.location}
            onChangeText={(v) => updateTier1('location', v)}
            placeholder="e.g. Pacific Northwest, US"
            placeholderTextColor={theme.textMuted}
          />
        </View>

        <Text style={styles.sectionTitle}>Sensitive info (optional)</Text>
        <Text style={styles.sectionSubtitle}>
          Each field below has its own switches for how it can be used - leave both off to store
          it without using it for anything yet.
        </Text>

        {TIER2_FIELDS.map(({ key, label }) => (
          <View key={key} style={styles.tier2Card}>
            <Text style={styles.label}>{label}</Text>
            <TextInput
              style={styles.input}
              value={tier2Fields[key] != null ? String(tier2Fields[key]) : ''}
              onChangeText={(v) => updateTier2Field(key, v)}
              placeholderTextColor={theme.textMuted}
            />
            <View style={styles.consentRow}>
              <TouchableOpacity
                style={styles.consentToggle}
                onPress={() => toggleConsent(key, 'used_for_personalization')}
              >
                <Ionicons
                  name={tier2Consent[key]?.used_for_personalization ? 'checkbox' : 'square-outline'}
                  size={20}
                  color={tier2Consent[key]?.used_for_personalization ? theme.accent : theme.textMuted}
                />
                <Text style={styles.consentLabel}>Personalize reading</Text>
              </TouchableOpacity>
              <TouchableOpacity
                style={styles.consentToggle}
                onPress={() => toggleConsent(key, 'used_for_feed_relevance')}
              >
                <Ionicons
                  name={tier2Consent[key]?.used_for_feed_relevance ? 'checkbox' : 'square-outline'}
                  size={20}
                  color={tier2Consent[key]?.used_for_feed_relevance ? theme.accent : theme.textMuted}
                />
                <Text style={styles.consentLabel}>Match my feed</Text>
              </TouchableOpacity>
            </View>
          </View>
        ))}

        <TouchableOpacity style={styles.saveButton} onPress={handleSave} disabled={saving}>
          <Text style={styles.saveButtonText}>
            {saving ? 'Saving...' : saved ? 'Saved' : 'Save Profile'}
          </Text>
        </TouchableOpacity>
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: theme.background,
  },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingHorizontal: 10,
    paddingVertical: 10,
    borderBottomWidth: 1.5,
    borderBottomColor: theme.border,
    backgroundColor: theme.surface,
  },
  headerButton: {
    width: 34,
    padding: 5,
  },
  headerTitle: {
    fontFamily: theme.serif,
    fontSize: 18,
    fontWeight: 'bold',
    color: theme.text,
  },
  content: {
    padding: 20,
    paddingBottom: 40,
  },
  disclaimer: {
    fontSize: 13,
    color: theme.textMuted,
    marginBottom: 20,
    lineHeight: 18,
  },
  sectionTitle: {
    fontFamily: theme.serif,
    fontSize: 18,
    fontWeight: 'bold',
    color: theme.text,
    marginTop: 10,
    marginBottom: 10,
  },
  sectionSubtitle: {
    fontSize: 13,
    color: theme.textMuted,
    marginBottom: 14,
  },
  field: {
    marginBottom: 14,
  },
  label: {
    fontSize: 13,
    color: theme.textMuted,
    marginBottom: 6,
  },
  input: {
    borderWidth: 1.5,
    borderColor: theme.border,
    borderRadius: 10,
    paddingHorizontal: 14,
    paddingVertical: 10,
    fontSize: 15,
    color: theme.text,
    backgroundColor: theme.surface,
  },
  tier2Card: {
    backgroundColor: theme.surface,
    borderWidth: 1.5,
    borderColor: theme.border,
    borderRadius: 10,
    padding: 14,
    marginBottom: 12,
  },
  consentRow: {
    flexDirection: 'row',
    gap: 16,
    marginTop: 10,
  },
  consentToggle: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
  },
  consentLabel: {
    fontSize: 12,
    color: theme.textMuted,
  },
  saveButton: {
    backgroundColor: theme.accent,
    borderWidth: 1.5,
    borderColor: theme.border,
    borderRadius: 10,
    height: 52,
    alignItems: 'center',
    justifyContent: 'center',
    marginTop: 10,
  },
  saveButtonText: {
    fontSize: 16,
    fontWeight: 'bold',
    color: theme.surface,
  },
  centerContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    padding: 20,
  },
  emptyText: {
    fontSize: 15,
    color: theme.textMuted,
    textAlign: 'center',
    marginTop: 10,
  },
  loginButton: {
    backgroundColor: theme.accent,
    borderWidth: 1.5,
    borderColor: theme.border,
    borderRadius: 10,
    paddingVertical: 10,
    paddingHorizontal: 30,
    marginTop: 16,
  },
  loginButtonText: {
    color: theme.text,
    fontSize: 15,
    fontWeight: 'bold',
  },
});
