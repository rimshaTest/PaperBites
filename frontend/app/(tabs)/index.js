import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  FlatList,
  StyleSheet,
  ActivityIndicator,
  RefreshControl,
  SafeAreaView
} from 'react-native';
import { useRouter } from 'expo-router';
import PaperCard from '../../components/PaperCard';
import LoadingIndicator from '../../components/LoadingIndicator';
import ErrorMessage from '../../components/ErrorMessage';
import { fetchPapers } from '../../services/api';
import { useFavoritePapers } from '../../hooks/useStorage';
import { useAuth } from '../../hooks/useAuth';
import theme from '../../constants/theme';

export default function HomeScreen() {
  const router = useRouter();
  const { user, token } = useAuth();
  const { isFavorite, toggleFavorite } = useFavoritePapers(token);
  const [papers, setPapers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState(null);
  const [page, setPage] = useState(0);
  const [hasMore, setHasMore] = useState(true);
  const PAGE_SIZE = 10;

  // Load initial papers
  useEffect(() => {
    loadPapers();
  }, []);

  // Function to load papers - the feed is papers fetched via the free-API pipeline
  // (Semantic Scholar/OpenAlex), not videos; video generation is a backburner feature.
  const loadPapers = async (refresh = false) => {
    try {
      if (refresh) {
        setPage(0);
        setHasMore(true);
      }

      if (!hasMore && !refresh) return;

      const pageToLoad = refresh ? 0 : page;
      setLoading(true);
      setError(null);

      const fetchedPapers = await fetchPapers({
        limit: PAGE_SIZE,
        offset: pageToLoad * PAGE_SIZE,
      });

      if (fetchedPapers.length < PAGE_SIZE) {
        setHasMore(false);
      }

      setPapers(prev => refresh ? fetchedPapers : [...prev, ...fetchedPapers]);
      setPage(pageToLoad + 1);
    } catch (err) {
      setError(`Failed to load papers: ${err.message}`);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  // Handle pull-to-refresh
  const handleRefresh = () => {
    setRefreshing(true);
    loadPapers(true);
  };

  // Handle reaching end of list (load more)
  const handleEndReached = () => {
    if (!loading && hasMore) {
      loadPapers();
    }
  };

  // Handle paper card press
  const handlePaperPress = (paper) => {
    router.push(`/paper/${paper.id}`);
  };

  // Bookmarking requires an account; send signed-out users to log in instead
  const handleToggleBookmark = (paper) => {
    if (!user) {
      router.push('/login');
      return;
    }
    toggleFavorite(paper);
  };

  // Empty component shown when no papers
  const renderEmptyComponent = () => (
    <View style={styles.emptyContainer}>
      {loading ? (
        <ActivityIndicator size="large" color={theme.accent} />
      ) : (
        <Text style={styles.emptyText}>
          {error || "No papers found. Pull down to refresh."}
        </Text>
      )}
    </View>
  );

  // Footer component shown when loading more
  const renderFooter = () => {
    if (!loading || papers.length === 0) return null;
    return (
      <View style={styles.footerContainer}>
        <ActivityIndicator size="small" color={theme.accent} />
        <Text style={styles.footerText}>Loading more papers...</Text>
      </View>
    );
  };

  if (loading && papers.length === 0) {
    return <LoadingIndicator message="Loading research papers..." />;
  }

  if (error && papers.length === 0) {
    return (
      <ErrorMessage
        message={error}
        onRetry={() => loadPapers(true)}
      />
    );
  }

  return (
    <SafeAreaView style={styles.container}>
      <View style={styles.header}>
        <View style={styles.headerSpacer} />
        <Text style={styles.title}>PaperBites</Text>
        <View style={styles.headerSpacer} />
      </View>

      <FlatList
        data={papers}
        renderItem={({ item }) => (
          <PaperCard
            paper={item}
            onPress={handlePaperPress}
            isBookmarked={isFavorite(item.id)}
            onToggleBookmark={handleToggleBookmark}
          />
        )}
        keyExtractor={item => item.id}
        ListEmptyComponent={renderEmptyComponent}
        ListFooterComponent={renderFooter}
        onEndReached={handleEndReached}
        onEndReachedThreshold={0.3}
        refreshControl={
          <RefreshControl
            refreshing={refreshing}
            onRefresh={handleRefresh}
            colors={[theme.accent]}
          />
        }
        showsVerticalScrollIndicator={false}
        contentContainerStyle={papers.length === 0 ? styles.listContentEmpty : styles.listContent}
      />
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
    paddingHorizontal: 16,
    paddingVertical: 16,
    backgroundColor: theme.surface,
    borderBottomWidth: 1.5,
    borderBottomColor: theme.border,
  },
  headerSpacer: {
    width: 32,
  },
  title: {
    flex: 1,
    fontFamily: theme.serif,
    fontSize: 20,
    fontWeight: 'bold',
    color: theme.text,
    textAlign: 'center',
  },
  listContent: {
    paddingVertical: 10,
  },
  listContentEmpty: {
    flexGrow: 1,
    justifyContent: 'center',
  },
  emptyContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    padding: 20,
  },
  emptyText: {
    fontSize: 16,
    color: theme.textMuted,
    textAlign: 'center',
  },
  footerContainer: {
    flexDirection: 'row',
    justifyContent: 'center',
    alignItems: 'center',
    paddingVertical: 15,
  },
  footerText: {
    fontSize: 14,
    color: theme.textMuted,
    marginLeft: 8,
  },
});
