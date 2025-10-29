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
import VideoCard from '../components/VideoCard';
import LoadingIndicator from '../components/LoadingIndicator';
import ErrorMessage from '../components/ErrorMessage';
import { fetchVideos } from '../services/api';
import Colors from '../constants/Colors';

export default function HomeScreen() {
  const router = useRouter();
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

  // Empty component shown when no videos
  const renderEmptyComponent = () => (
    <View style={styles.emptyContainer}>
      {loading ? (
        <ActivityIndicator size="large" color="#4285F4" />
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
        <ActivityIndicator size="small" color="#4285F4" />
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
        <Text style={styles.title}>PaperBites</Text>
      </View>
      
      <FlatList
        data={videos}
        renderItem={({ item }) => (
          <VideoCard video={item} onPress={handleVideoPress} />
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
            colors={['#4285F4']}
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
    backgroundColor: '#f9f9f9',
  },
  header: {
    padding: 16,
    backgroundColor: '#fff',
    borderBottomWidth: 1,
    borderBottomColor: '#eee',
  },
  title: {
    fontSize: 20,
    fontWeight: 'bold',
    color: '#333',
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
    color: '#666',
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
    color: '#666',
    marginLeft: 8,
  },
});