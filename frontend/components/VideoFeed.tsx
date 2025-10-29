// components/VideoFeed.tsx
import * as React from 'react';
import { 
  View, 
  FlatList, 
  Dimensions, 
  StyleSheet, 
  Text, 
  ActivityIndicator, 
  Platform 
} from 'react-native';
import { Video, ResizeMode } from 'expo-av';
import { fetchCloudinaryVideos } from '../services/cloudinaryService';

const { width, height } = Dimensions.get('window');

interface VideoItem {
  id: string;
  title: string;
  videoUrl: string;
  thumbnail?: string;
}

const VideoFeed: React.FC = () => {
  const [videos, setVideos] = React.useState<VideoItem[]>([]);
  const [loading, setLoading] = React.useState(true);
  const [error, setError] = React.useState<string | null>(null);
  const [activeVideoIndex, setActiveVideoIndex] = React.useState(0);
  
  const flatListRef = React.useRef<FlatList>(null);
  
  // Fetch videos from Cloudinary
  React.useEffect(() => {
    const loadVideos = async () => {
      try {
        setLoading(true);
        const videosData = await fetchCloudinaryVideos();
        setVideos(videosData ?? []);
      } catch (err) {
        setError('Failed to load videos');
        console.error(err);
      } finally {
        setLoading(false);
      }
    };
    
    loadVideos();
  }, []);
  
  // Track which video is currently visible for playback
  const onViewableItemsChanged = React.useRef(
    ({ viewableItems }: { viewableItems: Array<{ index: number | null }> }) => {
      if (viewableItems.length > 0 && viewableItems[0].index !== null && viewableItems[0].index !== undefined) {
        setActiveVideoIndex(viewableItems[0].index);
      }
    }
  ).current;
  
  const viewabilityConfig = {
    itemVisiblePercentThreshold: 50
  };
  
  // Render a video item
  const renderVideoItem = ({ item, index }: { item: VideoItem; index: number }) => {
    const isActive = index === activeVideoIndex;
    
    // For web platform, use HTML5 video element
    if (Platform.OS === 'web') {
      return (
        <View style={styles.videoContainer}>
          <div style={styles.videoWrapper as any}>
            <video
              src={item.videoUrl}
              style={{
                width: '100%',
                height: '100%',
                objectFit: 'contain'
              }}
              controls
              autoPlay={isActive}
              loop
              playsInline
              poster={item.thumbnail}
              muted={!isActive}
            />
          </div>
          <View style={styles.videoInfo}>
            <Text style={styles.videoTitle}>{item.title}</Text>
          </View>
        </View>
      );
    }
    
    // For native platforms, use expo-av
    return (
      <View style={styles.videoContainer}>
        <View style={styles.videoWrapper}>
          <Video
            source={{ uri: item.videoUrl }}
            style={styles.video}
            useNativeControls
            resizeMode={ResizeMode.CONTAIN}
            shouldPlay={isActive}
            isLooping
            isMuted={!isActive}
          />
        </View>
        <View style={styles.videoInfo}>
          <Text style={styles.videoTitle}>{item.title}</Text>
        </View>
      </View>
    );
  };
  
  if (loading) {
    return (
      <View style={styles.centerContainer}>
        <ActivityIndicator size="large" color="#0066cc" />
        <Text style={styles.loadingText}>Loading videos...</Text>
      </View>
    );
  }
  
  if (error) {
    return (
      <View style={styles.centerContainer}>
        <Text style={styles.errorText}>{error}</Text>
      </View>
    );
  }
  
  if (videos.length === 0) {
    return (
      <View style={styles.centerContainer}>
        <Text style={styles.messageText}>No videos found</Text>
      </View>
    );
  }
  
  return (
    <FlatList
      ref={flatListRef}
      data={videos}
      keyExtractor={(item) => item.id}
      renderItem={renderVideoItem}
      pagingEnabled
      snapToInterval={height}
      snapToAlignment="start"
      decelerationRate="fast"
      showsVerticalScrollIndicator={false}
      onViewableItemsChanged={onViewableItemsChanged}
      viewabilityConfig={viewabilityConfig}
      initialNumToRender={2}
      maxToRenderPerBatch={3}
      windowSize={5}
      removeClippedSubviews={true}
      style={styles.list}
    />
  );
};

const styles = StyleSheet.create({
  list: {
    flex: 1,
  },
  videoContainer: {
    height,
    width,
    backgroundColor: '#000',
  },
  videoWrapper: {
    flex: 1,
  },
  video: {
    flex: 1,
  },
  videoInfo: {
    position: 'absolute',
    bottom: 80,
    left: 0,
    right: 0,
    padding: 20,
  },
  videoTitle: {
    color: '#fff',
    fontSize: 18,
    fontWeight: 'bold'
  },
  centerContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    padding: 20,
  },
  loadingText: {
    marginTop: 10,
    fontSize: 16,
    color: '#666',
  },
  errorText: {
    fontSize: 16,
    color: '#e74c3c',
    textAlign: 'center',
  },
  messageText: {
    fontSize: 16,
    color: '#666',
    textAlign: 'center',
  },
});

export default VideoFeed;