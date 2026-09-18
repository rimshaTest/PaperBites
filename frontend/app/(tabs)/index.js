import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  FlatList,
  StyleSheet,
  ActivityIndicator,
  RefreshControl,
  TouchableOpacity,
  SafeAreaView
} from 'react-native';
import { useRouter } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import VideoCard from '../../components/VideoCard';
import LoadingIndicator from '../../components/LoadingIndicator';
import ErrorMessage from '../../components/ErrorMessage';
import { fetchVideos } from '../../services/api';
import { useFavoriteVideos } from '../../hooks/useStorage';
import { useAuth } from '../../hooks/useAuth';
import theme from '../../constants/theme';

export default function HomeScreen() {
  const router = useRouter();
  const { user, token } = useAuth();
  const { isFavorite, toggleFavorite } = useFavoriteVideos(token);
  const [videos, setVideos] = useState([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState(null);
  const [page, setPage] = useState(0);
  const [hasMore, setHasMore] = useState(true);
  const PAGE_SIZE = 10;

  // Load initial videos
  useEffect(() => {
    loadVideos();
  }, []);

  // Function to load videos
  const loadVideos = async (refresh = false) => {
    try {
      if (refresh) {
        setPage(0);
        setHasMore(true);
      }

      if (!hasMore && !refresh) return;

      const pageToLoad = refresh ? 0 : page;
      setLoading(true);
      setError(null);

      const fetchedVideos = await fetchVideos({
        limit: PAGE_SIZE,
        offset: pageToLoad * PAGE_SIZE,
      });

      if (fetchedVideos.length < PAGE_SIZE) {
        setHasMore(false);
      }

      setVideos(prev => refresh ? fetchedVideos : [...prev, ...fetchedVideos]);
      setPage(pageToLoad + 1);
    } catch (err) {
      setError(`Failed to load videos: ${err.message}`);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  // Handle pull-to-refresh
  const handleRefresh = () => {
    setRefreshing(true);
    loadVideos(true);
  };

  // Handle reaching end of list (load more)
  const handleEndReached = () => {
    if (!loading && hasMore) {
      loadVideos();
    }
  };

  // Handle video card press
  const handleVideoPress = (video) => {
    router.push(`/video/${video.id}`);
  };

  // Bookmarking requires an account; send signed-out users to log in instead
  const handleToggleBookmark = (video) => {
    if (!user) {
      router.push('/login');
      return;
    }
    toggleFavorite(video);
  };

  // Empty component shown when no videos
  const renderEmptyComponent = () => (
    <View style={styles.emptyContainer}>
      {loading ? (
        <ActivityIndicator size="large" color={theme.accent} />
      ) : (
        <Text style={styles.emptyText}>
          {error || "No videos found. Pull down to refresh."}
        </Text>
      )}
    </View>
  );

  // Footer component shown when loading more
  const renderFooter = () => {
    if (!loading || videos.length === 0) return null;
    return (
      <View style={styles.footerContainer}>
        <ActivityIndicator size="small" color={theme.accent} />
        <Text style={styles.footerText}>Loading more videos...</Text>
      </View>
    );
  };

  if (loading && videos.length === 0) {
    return <LoadingIndicator message="Loading research videos..." />;
  }

  if (error && videos.length === 0) {
    return (
      <ErrorMessage
        message={error}
        onRetry={() => loadVideos(true)}
      />
    );
  }

  return (
    <SafeAreaView style={styles.container}>
      <View style={styles.header}>
        <View style={styles.headerSpacer} />
        <Text style={styles.title}>PaperBites</Text>
        <TouchableOpacity
          style={styles.searchButton}
          onPress={() => router.push('/search')}
        >
          <Ionicons name="search-outline" size={22} color={theme.text} />
        </TouchableOpacity>
      </View>

      <FlatList
        data={videos}
        renderItem={({ item }) => (
          <VideoCard
            video={item}
            onPress={handleVideoPress}
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
        contentContainerStyle={videos.length === 0 ? styles.listContentEmpty : styles.listContent}
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
  searchButton: {
    width: 32,
    alignItems: 'flex-end',
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
