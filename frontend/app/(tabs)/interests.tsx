import * as React from 'react';
import {
  View,
  Text,
  TouchableOpacity,
  StyleSheet,
  ScrollView,
  ActivityIndicator,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useRouter } from 'expo-router';
import { useBottomTabBarHeight } from 'expo-router/js-tabs';
import { Ionicons } from '@expo/vector-icons';
import { fetchCategories, fetchInterests, saveInterests } from '../../services/api';
import { useAuth } from '../../hooks/useAuth';
import { useTheme } from '../../hooks/useTheme';

export default function InterestsScreen() {
  const router = useRouter();
  const { user, token, loading: authLoading } = useAuth();
  const { theme } = useTheme();
  const tabBarHeight = useBottomTabBarHeight();
  const styles = React.useMemo(() => createStyles(theme), [theme]);
  const [topics, setTopics] = React.useState<string[]>([]);
  const [selected, setSelected] = React.useState<string[]>([]);
  const [loading, setLoading] = React.useState(true);
  const [saved, setSaved] = React.useState(false);

  React.useEffect(() => {
    if (!token) {
      setLoading(false);
      return;
    }

    const load = async () => {
      try {
        setLoading(true);
        const [fetchedTopics, savedInterests] = await Promise.all([
          fetchCategories(),
          fetchInterests(token),
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
  }, [token]);

  const toggleTopic = (topic: string) => {
    setSaved(false);
    setSelected((prev) =>
      prev.includes(topic) ? prev.filter((t) => t !== topic) : [...prev, topic]
    );
  };

  const handleSave = async () => {
    if (!token) return;
    await saveInterests(token, selected);
    setSaved(true);
  };

  return (
    <SafeAreaView style={styles.container}>
      <View style={styles.header}>
        <TouchableOpacity onPress={() => router.back()} style={styles.headerButton}>
          <Ionicons name="arrow-back" size={24} color={theme.text} />
        </TouchableOpacity>
        <Text style={styles.headerTitle}>Interests</Text>
        <View style={styles.headerButton} />
      </View>

      {authLoading || (loading && token) ? (
        <ActivityIndicator style={{ marginTop: 40 }} size="large" color={theme.text} />
      ) : !user ? (
        <View style={styles.centerContainer}>
          <Ionicons name="lock-closed-outline" size={40} color={theme.textMuted} />
          <Text style={styles.emptyText}>Log in to pick your interests and shape your feed.</Text>
          <TouchableOpacity style={styles.loginButton} onPress={() => router.push('/login')}>
            <Text style={styles.loginButtonText}>Log In</Text>
          </TouchableOpacity>
        </View>
      ) : (
        <>
          <Text style={styles.subtitle}>
            Pick the topics, journals, or authors you care about. Your home feed will follow.
          </Text>

          {topics.length === 0 ? (
            <Text style={styles.emptyText}>
              No topics available yet - check back once more papers have been added.
            </Text>
          ) : (
            <ScrollView style={styles.chipScroll} contentContainerStyle={styles.chipContainer}>
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

          <TouchableOpacity
            style={[styles.saveButton, { marginBottom: tabBarHeight + 12 }]}
            onPress={handleSave}
          >
            <Text style={styles.saveButtonText}>{saved ? 'Saved' : 'Save Interests'}</Text>
          </TouchableOpacity>
        </>
      )}
    </SafeAreaView>
  );
}

const createStyles = (theme: any) => StyleSheet.create({
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
  headerTitle: {
    fontFamily: theme.serif,
    fontSize: 18,
    fontWeight: 'bold',
    color: theme.text,
  },
  headerButton: {
    width: 34,
    padding: 5,
  },
  subtitle: {
    fontSize: 14,
    color: theme.textMuted,
    paddingHorizontal: 16,
    paddingVertical: 14,
    marginHorizontal: 20,

  },
  centerContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    paddingHorizontal: 16,
    paddingVertical: 14,
    marginHorizontal: 20,
  },
  emptyText: {
    fontSize: 14,
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
  chipScroll: {
    flex: 1,
  },
  chipContainer: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 10,
    paddingHorizontal: 16,
    paddingVertical: 14,
    marginHorizontal: 20,
  },
  chip: {
    borderWidth: 1.5,
    borderColor: theme.border,
    borderRadius: 20,
    paddingHorizontal: 16,
    paddingVertical: 10,
    backgroundColor: theme.surface,
    flexBasis: '47%',
    flexGrow: 1,
    alignItems: 'center',
    justifyContent: 'center',
  },
  chipSelected: {
    backgroundColor: theme.accent,
  },
  chipText: {
    fontSize: 14,
    lineHeight: 20,
    includeFontPadding: false,
    textAlign: 'center',
    fontWeight: 'bold',
    color: theme.text,
  },
  chipTextSelected: {
    fontWeight: 'bold',
  },
  saveButton: {
    backgroundColor: theme.accent,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 6,
    borderRadius: 10,
    paddingVertical: 12,
    marginHorizontal: 20,
  },
  saveButtonText: {
    fontSize: 14,
    fontWeight: 'bold',
    color: theme.text,
  },
});
