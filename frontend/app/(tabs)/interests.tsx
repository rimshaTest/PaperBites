import * as React from 'react';
import {
  View,
  Text,
  TouchableOpacity,
  StyleSheet,
  ScrollView,
  ActivityIndicator,
} from 'react-native';
import {SafeAreaView} from 'react-native-safe-area-context';
import { fetchCategories } from '../../services/api';
import { getInterests, saveInterests } from '../../services/storage';
import theme from '../../constants/theme';

export default function InterestsScreen() {
  const [topics, setTopics] = React.useState<string[]>([]);
  const [selected, setSelected] = React.useState<string[]>([]);
  const [loading, setLoading] = React.useState(true);
  const [saved, setSaved] = React.useState(false);

  React.useEffect(() => {
    const load = async () => {
      try {
        setLoading(true);
        const [fetchedTopics, savedInterests] = await Promise.all([
          fetchCategories(),
          getInterests(),
        ]);
        setTopics(fetchedTopics ?? []);
        setSelected(savedInterests ?? []);
      } catch (err) {
        console.error('Failed to load topics:', err);
        setTopics([]);
      } finally {
        setLoading(false);
      }
    };
    load();
  }, []);

  const toggleTopic = (topic: string) => {
    setSaved(false);
    setSelected((prev) =>
      prev.includes(topic) ? prev.filter((t) => t !== topic) : [...prev, topic]
    );
  };

  const handleSave = async () => {
    await saveInterests(selected);
    setSaved(true);
  };

  return (
    <SafeAreaView style={styles.container}>
      <View style={styles.header}>
        <Text style={styles.headerTitle}>Interests</Text>
      </View>
      <Text style={styles.subtitle}>
        Pick the topics, journals, or authors you care about. Your home feed will follow.
      </Text>

      {loading ? (
        <ActivityIndicator style={{ marginTop: 40 }} size="large" color={theme.text} />
      ) : topics.length === 0 ? (
        <Text style={styles.emptyText}>
          No topics available yet - check back once more papers have been added.
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

      <TouchableOpacity style={styles.saveButton} onPress={handleSave}>
        <Text style={styles.saveButtonText}>{saved ? 'Saved' : 'Save Interests'}</Text>
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
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
  },
  headerTitle: {
    fontFamily: theme.serif,
    fontSize: 28,
    fontWeight: 'bold',
    color: theme.text,
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
  saveButton: {
    backgroundColor: theme.accent,
    borderWidth: 1.5,
    borderColor: theme.border,
    borderRadius: 10,
    height: 52,
    alignItems: 'center',
    justifyContent: 'center',
    marginTop: 10,
    marginBottom: 10,
  },
  saveButtonText: {
    fontSize: 16,
    fontWeight: 'bold',
    color: theme.surface,
  },
});
