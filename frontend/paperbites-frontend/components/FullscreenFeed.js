// components/FullscreenFeed.js
import React, { useState, useRef, useEffect } from 'react';
import { 
  View, 
  FlatList, 
  Dimensions, 
  StyleSheet, 
  ActivityIndicator,
  Text,
  TouchableOpacity,
  StatusBar,
  SafeAreaView
} from 'react-native';
import { useRouter } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import { fetchVideos } from '../services/api';
import FullscreenVideoPlayer from './FullscreenVideoPlayer';
import { addToWatchHistory } from '../services/storage';

const { width, height } = Dimensions.get('window');

const FullscreenFeed = ({ initialVideoId, initialVideos = null }) => {
  const router = useRouter();
  const [videos, setVideos] = useState(initialVideos || []);
  const [loading, setLoading] = useState(initialVideos ? false : true);
  const [error, setError] = useState(null);
  const [activeVideoIndex, setActiveVideoIndex] = useState(0);
  const [hasMore, setHasMore] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [page, setPage] = useState(0);
  const PAGE_SIZE = 10; // Load more videos at once for smoother scrolling
  
  const flatListRef = useRef(null);

  // Load initial videos if not provided
  useEffect(() => {
    if (!initialVideos) {
      loadVideos();
    }
  }, [initialVideos]);

  // If initial videos were provided, find the appropriate starting index
  useEffect(() => {
    if (initialVideos && initialVideos.length > 0 && initialVideoId) {
      const foundIndex = initialVideos.findIndex(v => v.id === initialVideoId);
      if (foundIndex !== -1) {
        setActiveVideoIndex(foundIndex);
        // Scroll to the initial video after rendering
        setTimeout(() => {
          if (flatListRef.current) {
            flatListRef.current.scrollToIndex({ 
              index: foundIndex, 
              animated: false 
            });
          }
        }, 100);
      }
    }
  }, [initialVideos, initialVideoId]);

  // Handle changing videos and adding to watch history
  useEffect(() => {
    if (videos.length > 0 && activeVideoIndex >= 0) {
      const currentVideo = videos[activeVideoIndex];
      // Add to watch history
      addToWatchHistory(currentVideo);
    }
  }, [activeVideoIndex, videos]);

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

      // Find the initial video index if specified
      let initialIndex = 0;
      if (initialVideoId && refresh) {
        const foundIndex = fetchedVideos.findIndex(v => v.id === initialVideoId);
        if (foundIndex !== -1) {
          initialIndex = foundIndex;
        }
      }

      setVideos(prev => refresh ? fetchedVideos : [...prev, ...fetchedVideos]);
      setPage(pageToLoad + 1);
      
      // Scroll to initial video if refreshing
      if (refresh && flatListRef.current && initialIndex > 0) {
        setTimeout(() => {
          flatListRef.current.scrollToIndex({ index: initialIndex, animated: false });
        }, 100);
      }
    } catch (err) {
      setError(`Failed to load videos: ${err.message}`);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  // Handle scroll events to determine active video
  const handleViewableItemsChanged = useRef(({ viewableItems }) => {
    if (viewableItems.length > 0) {
      setActiveVideoIndex(viewableItems[0].index);
    }
  }).current;

  // Viewability config - item is considered viewable when it's fully on screen
  const viewabilityConfig = useRef({
    itemVisiblePercentThreshold: 90
  }).current;

  // Render a video item
  const renderItem = ({ item, index }) => {
    const isActive = index === activeVideoIndex;
    
    return (
      <View style={styles.container}>
        <StatusBar translucent backgroundColor="transparent" barStyle="light-content" />
        <FullscreenVideoPlayer
          video={item}
          isActive={isActive}
          onShare={() => handleShare(item)}
          onMoreInfo={() => handleMoreInfo(item)}
        />
      </View>
    );
  };

  // Handle "More Info" button press
  const handleMoreInfo = (video) => {
    router.push(`/video/${video.id}`);
  };

  // Handle Share button press
  const handleShare = (video) => {
    // You can implement share functionality here
    console.log('Share video:', video.id);
  };

  // Handle end reached - load more videos
  const handleEndReached = () => {
    if (!loading && hasMore) {
      loadVideos();
    }
  };

  // Render loading indicator
  const renderLoading = () => (
    <View style={styles.loadingContainer}>
      <ActivityIndicator size="large" color="#fff" />
      <Text style={styles.loadingText}>Loading videos...</Text>
    </View>
  );

  // Render error message
  const renderError = () => (
    <View style={styles.errorContainer}>
      <Text style={styles.errorText}>{error}</Text>
      <TouchableOpacity onPress={() => loadVideos(true)} style={styles.retryButton}>
        <Text style={styles.retryText}>Retry</Text>
      </TouchableOpacity>
    </View>
  );

  return (
    <View style={styles.container}>
      <StatusBar translucent backgroundColor="transparent" barStyle="light-content" />

      {loading && videos.length === 0 ? (
        renderLoading()
      ) : error && videos.length === 0 ? (
        renderError()
      ) : (
        <FlatList
          ref={flatListRef}
          data={videos}
          renderItem={renderItem}
          keyExtractor={item => item.id}
          snapToInterval={height}
          snapToAlignment="start"
          decelerationRate="fast"
          pagingEnabled
          showsVerticalScrollIndicator={false}
          onViewableItemsChanged={handleViewableItemsChanged}
          viewabilityConfig={viewabilityConfig}
          onEndReached={handleEndReached}
          onEndReachedThreshold={0.5}
          initialNumToRender={3}
          maxToRenderPerBatch={5}
          windowSize={7}
          removeClippedSubviews={true}
          ListFooterComponent={
            hasMore ? (
              <View style={styles.footer}>
                <ActivityIndicator color="#fff" size="large" />
              </View>
            ) : null
          }
        />
      )}
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#000',
  },
  topControls: {
    position: 'absolute',
    top: 0,
    left: 0,
    right: 0,
    zIndex: 10,
    paddingTop: 40, // Account for status bar
    paddingHorizontal: 16,
  },
  backButton: {
    width: 40,
    height: 40,
    borderRadius: 20,
    backgroundColor: 'rgba(0, 0, 0, 0.3)',
    justifyContent: 'center',
    alignItems: 'center',
  },
  loadingContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
  },
  loadingText: {
    color: '#fff',
    marginTop: 12,
    fontSize: 16,
  },
  errorContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    padding: 20,
  },
  errorText: {
    color: '#fff',
    fontSize: 16,
    marginBottom: 20,
    textAlign: 'center',
  },
  retryButton: {
    paddingHorizontal: 20,
    paddingVertical: 10,
    backgroundColor: '#4285F4',
    borderRadius: 5,
  },
  retryText: {
    color: '#fff',
    fontWeight: 'bold',
  },
  footer: {
    height: 100,
    justifyContent: 'center',
    alignItems: 'center',
  },
});

export default FullscreenFeed;