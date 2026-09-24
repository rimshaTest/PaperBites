import React, { useState } from 'react';
import {
  View,
  Text,
  TextInput,
  TouchableOpacity,
  FlatList,
  StyleSheet,
  ActivityIndicator,
  SafeAreaView,
} from 'react-native';
import { useRouter } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import PaperCard from '../components/PaperCard';
import { searchPapersSemantically } from '../services/api';
import { useAuth } from '../hooks/useAuth';
import { useFavoritePapers } from '../hooks/useStorage';
import theme from '../constants/theme';

/**
 * Semantic paper search, reached from the search icon on Home's card overlay
 * (components/PaperFeed.tsx). Ranks by meaning via the backend's Gemini-embedded papers
 * (backend/paper/embeddings.py), not just exact keyword matches - separate from Interests'
 * hard category filter, not blended with it. No login required to search or view results;
 * bookmarking a result still routes through login like anywhere else in the app.
 */
export default function SearchScreen() {
  const router = useRouter();
  const { user, token } = useAuth();
  const { isFavorite, toggleFavorite } = useFavoritePapers(token);

  const [query, setQuery] = useState('');
  const [searching, setSearching] = useState(false);
  const [results, setResults] = useState(null);
  const [error, setError] = useState(null);

  const handleSearch = async () => {
    if (!query.trim()) return;
    setSearching(true);
    setError(null);
    try {
      const papers = await searchPapersSemantically(query.trim());
      setResults(papers ?? []);
    } catch (err) {
      console.error('Semantic search failed:', err);
      setError(err.message || 'Search failed. Try again.');
      setResults([]);
    } finally {
      setSearching(false);
    }
  };

  const handlePaperPress = (paper) => router.push(`/paper/${paper.id}`);
  const handleAuthorPress = (author) => router.push(`/author/${encodeURIComponent(author.id)}`);
  const handleJournalPress = (journal) => router.push(`/journal/${encodeURIComponent(journal)}`);

  const handleToggleBookmark = (paper) => {
    if (!user) {
      router.push('/login');
      return;
    }
    toggleFavorite(paper);
  };

  return (
    <SafeAreaView style={styles.container}>
      <View style={styles.header}>
        <TouchableOpacity onPress={() => router.back()} hitSlop={12}>
          <Ionicons name="close" size={26} color={theme.text} />
        </TouchableOpacity>
        <Text style={styles.headerTitle}>Search</Text>
        <View style={{ width: 26 }} />
      </View>

      <View style={styles.searchBar}>
        <Ionicons name="search" size={18} color={theme.textMuted} />
        <TextInput
          style={styles.searchInput}
          placeholder="Search papers by topic or idea..."
          placeholderTextColor={theme.textMuted}
          value={query}
          onChangeText={setQuery}
          onSubmitEditing={handleSearch}
          returnKeyType="search"
          autoFocus
        />
        {searching && <ActivityIndicator size="small" color={theme.text} />}
      </View>

      {results === null ? (
        <View style={styles.centerContainer}>
          <Ionicons name="sparkles-outline" size={40} color={theme.textMuted} />
          <Text style={styles.emptyText}>
            Search matches papers by meaning, not just exact words - try describing the idea
            you're looking for.
          </Text>
        </View>
      ) : error ? (
        <View style={styles.centerContainer}>
          <Text style={styles.emptyText}>{error}</Text>
        </View>
      ) : results.length === 0 ? (
        <View style={styles.centerContainer}>
          <Ionicons name="search-outline" size={40} color={theme.textMuted} />
          <Text style={styles.emptyText}>No matching papers found. Try different wording.</Text>
        </View>
      ) : (
        <FlatList
          data={results}
          keyExtractor={(item) => item.id}
          renderItem={({ item }) => (
            <PaperCard
              paper={item}
              onPress={handlePaperPress}
              isBookmarked={isFavorite(item.id)}
              onToggleBookmark={() => handleToggleBookmark(item)}
              onAuthorPress={handleAuthorPress}
              onJournalPress={handleJournalPress}
            />
          )}
          showsVerticalScrollIndicator={false}
          contentContainerStyle={styles.resultsList}
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
    paddingVertical: 16,
    borderBottomWidth: 1.5,
    borderBottomColor: theme.border,
    backgroundColor: theme.surface,
  },
  headerTitle: {
    fontFamily: theme.serif,
    fontSize: 20,
    fontWeight: 'bold',
    color: theme.text,
  },
  searchBar: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 10,
    margin: 20,
    marginBottom: 10,
    paddingHorizontal: 14,
    height: 48,
    borderWidth: 1.5,
    borderColor: theme.border,
    borderRadius: 10,
    backgroundColor: theme.surface,
  },
  searchInput: {
    flex: 1,
    fontSize: 15,
    color: theme.text,
  },
  centerContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    padding: 30,
  },
  emptyText: {
    fontSize: 15,
    color: theme.textMuted,
    textAlign: 'center',
    marginTop: 10,
  },
  resultsList: {
    paddingVertical: 10,
  },
});
