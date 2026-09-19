import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  TouchableOpacity,
  StyleSheet,
  ScrollView,
  ActivityIndicator,
  SafeAreaView,
} from 'react-native';
import { useRouter } from 'expo-router';
import { fetchCategories, saveInterests } from '../services/api';
import { useAuth } from '../hooks/useAuth';
import theme from '../constants/theme';

/**
 * Shown once, right after a successful signup (see app/signup.js). Picking at least one
 * interest here immediately makes the home feed relevant instead of a generic recent-papers
 * list; skipping just means the feed stays unpersonalized until the user visits Interests
 * later from Profile > Settings > Manage Feed.
 */
export default function InterestsOnboardingScreen() {
  const router = useRouter();
  const { token } = useAuth();
  const [topics, setTopics] = useState([]);
  const [selected, setSelected] = useState([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    const load = async () => {
      try {
        setLoading(true);
        const fetchedTopics = await fetchCategories();
        setTopics(fetchedTopics ?? []);
      } catch (err) {
        console.error('Failed to load topics:', err);
        setTopics([]);
      } finally {
        setLoading(false);
      }
    };
    load();
  }, []);

  const toggleTopic = (topic) => {
    setSelected((prev) =>
      prev.includes(topic) ? prev.filter((t) => t !== topic) : [...prev, topic]
    );
  };

  const finish = () => router.replace('/(tabs)');

  const handleSkip = () => finish();

  const handleContinue = async () => {
    if (selected.length === 0 || !token) return;
    setSaving(true);
    try {
      await saveInterests(token, selected);
    } catch (err) {
      console.error('Failed to save interests:', err);
    } finally {
      setSaving(false);
      finish();
    }
  };

  return (
    <SafeAreaView style={styles.container}>
      <Text style={styles.title}>What are you into?</Text>
      <Text style={styles.subtitle}>
        Pick a few topics to shape your feed. You can change these anytime from Profile.
      </Text>

      {loading ? (
        <ActivityIndicator style={{ marginTop: 40 }} size="large" color={theme.text} />
      ) : topics.length === 0 ? (
        <Text style={styles.emptyText}>
          No topics available yet - you can pick these later from Profile.
        </Text>
      ) : (
        <ScrollView contentContainerStyle={styles.chipContainer}>
          {topics.map((topic) => {
            const isSelected = selected.includes(topic);
            return (
              <TouchableOpacity
                key={topic}
                style={[styles.chip, isSelected && styles.chipSelected]}
                onPress={() => toggleTopic(topic)}
              >
                <Text style={[styles.chipText, isSelected && styles.chipTextSelected]}>
                  {topic}
                </Text>
              </TouchableOpacity>
            );
          })}
        </ScrollView>
      )}

      <View style={styles.footer}>
        <TouchableOpacity style={styles.skipButton} onPress={handleSkip} disabled={saving}>
          <Text style={styles.skipButtonText}>Skip for now</Text>
        </TouchableOpacity>
        <TouchableOpacity
          style={[styles.continueButton, (selected.length === 0 || saving) && styles.continueButtonDisabled]}
          onPress={handleContinue}
          disabled={selected.length === 0 || saving}
        >
          <Text style={styles.continueButtonText}>{saving ? 'Saving...' : 'Continue'}</Text>
        </TouchableOpacity>
      </View>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: theme.background,
    padding: 20,
  },
  title: {
    fontFamily: theme.serif,
    fontSize: 26,
    fontWeight: 'bold',
    color: theme.text,
    marginTop: 10,
  },
  subtitle: {
    fontSize: 14,
    color: theme.textMuted,
    marginTop: 10,
    marginBottom: 20,
  },
  emptyText: {
    fontSize: 14,
    color: theme.textMuted,
    textAlign: 'center',
    marginTop: 40,
  },
  chipContainer: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 10,
    paddingBottom: 20,
  },
  chip: {
    borderWidth: 1.5,
    borderColor: theme.border,
    borderRadius: 20,
    paddingHorizontal: 16,
    paddingVertical: 10,
    backgroundColor: theme.surface,
  },
  chipSelected: {
    backgroundColor: theme.accent,
  },
  chipText: {
    fontSize: 14,
    color: theme.text,
  },
  chipTextSelected: {
    fontWeight: 'bold',
  },
  footer: {
    flexDirection: 'row',
    gap: 12,
    marginTop: 10,
    marginBottom: 10,
  },
  skipButton: {
    flex: 1,
    borderWidth: 1.5,
    borderColor: theme.border,
    borderRadius: 10,
    height: 52,
    alignItems: 'center',
    justifyContent: 'center',
  },
  skipButtonText: {
    fontSize: 16,
    fontWeight: 'bold',
    color: theme.text,
  },
  continueButton: {
    flex: 1,
    backgroundColor: theme.accent,
    borderWidth: 1.5,
    borderColor: theme.border,
    borderRadius: 10,
    height: 52,
    alignItems: 'center',
    justifyContent: 'center',
  },
  continueButtonDisabled: {
    opacity: 0.5,
  },
  continueButtonText: {
    fontSize: 16,
    fontWeight: 'bold',
    color: theme.surface,
  },
});
