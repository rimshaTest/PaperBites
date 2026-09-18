import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  FlatList,
  StyleSheet,
  TouchableOpacity,
  ActivityIndicator,
  Linking
} from 'react-native';
import {SafeAreaView} from 'react-native-safe-area-context';
import { useLocalSearchParams, useRouter } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import { fetchAuthor } from '../../services/api';
import theme from '../../constants/theme';

export default function AuthorProfileScreen() {
  const router = useRouter();
  const { id } = useLocalSearchParams();
  const [author, setAuthor] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const load = async () => {
      try {
        setLoading(true);
        const data = await fetchAuthor(id);
        setAuthor(data);
      } catch (err) {
        setError('Author not found');
      } finally {
        setLoading(false);
      }
    };

    if (id) {
      load();
    }
  }, [id]);

  return (
    <SafeAreaView style={styles.container}>
      <View style={styles.header}>
        <TouchableOpacity onPress={() => router.back()} style={styles.backButton}>
          <Ionicons name="arrow-back" size={22} color={theme.text} />
        </TouchableOpacity>
        <Text style={styles.headerTitle} numberOfLines={1}>{author?.name ?? 'Author'}</Text>
        <View style={{ width: 22 }} />
      </View>

      {loading ? (
        <ActivityIndicator style={{ marginTop: 40 }} size="large" color={theme.text} />
      ) : error ? (
        <Text style={styles.errorText}>{error}</Text>
      ) : (
        <FlatList
          data={author?.papers ?? []}
          keyExtractor={(item) => item.id}
          contentContainerStyle={styles.list}
          ListHeaderComponent={
            <Text style={styles.subtitle}>
              {author?.papers?.length ?? 0} paper{author?.papers?.length === 1 ? '' : 's'} in PaperBites
            </Text>
          }
          renderItem={({ item }) => (
            <TouchableOpacity
              style={styles.paperCard}
              onPress={() => item.url && Linking.openURL(item.url)}
            >
              <Text style={styles.paperTitle} numberOfLines={2}>{item.title}</Text>
              {item.journal && <Text style={styles.paperJournal}>{item.journal}</Text>}
              <View style={styles.paperMetaRow}>
                <Text style={styles.paperMeta}>{item.citation_count} citations</Text>
                {item.published_date && <Text style={styles.paperMeta}>{item.published_date}</Text>}
              </View>
            </TouchableOpacity>
          )}
        />
      )}
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
    paddingHorizontal: 20,
    paddingTop: 10,
    paddingBottom: 16,
  },
  backButton: {
    width: 22,
  },
  headerTitle: {
    flex: 1,
    fontFamily: theme.serif,
    fontSize: 18,
    fontWeight: 'bold',
    color: theme.text,
    textAlign: 'center',
    marginHorizontal: 10,
  },
  subtitle: {
    fontSize: 13,
    color: theme.textMuted,
    marginBottom: 12,
  },
  list: {
    paddingHorizontal: 20,
    paddingBottom: 20,
  },
  paperCard: {
    backgroundColor: theme.surface,
    borderWidth: 1.5,
    borderColor: theme.border,
    borderRadius: 10,
    padding: 14,
    marginBottom: 12,
  },
  paperTitle: {
    fontSize: 15,
    fontWeight: 'bold',
    color: theme.text,
    marginBottom: 6,
  },
  paperJournal: {
    fontSize: 12,
    color: theme.textMuted,
    marginBottom: 6,
  },
  paperMetaRow: {
    flexDirection: 'row',
    gap: 12,
  },
  paperMeta: {
    fontSize: 12,
    color: theme.textMuted,
  },
  errorText: {
    textAlign: 'center',
    color: theme.danger,
    marginTop: 40,
  },
});
