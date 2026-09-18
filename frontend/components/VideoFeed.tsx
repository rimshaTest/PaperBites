// components/VideoFeed.tsx
import * as React from 'react';
import { 
  View, 
  FlatList, 
  Dimensions, 
  StyleSheet, 
  Text,
  ActivityIndicator,
  Platform,
  TouchableOpacity
} from 'react-native';
import { useVideoPlayer, VideoView } from 'expo-video';
import { useRouter, useFocusEffect } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import { fetchVideos } from '../services/api';
import { getInterests } from '../services/storage';

const { width, height } = Dimensions.get('window');

interface VideoItem {
  id: string;
  title: string;
  videoUrl: string;
  thumbnail?: string;
  keywords?: string[];
}

// A dedicated component per list item so each gets its own expo-video player instance
// (useVideoPlayer is a hook and can't be called directly inside FlatList's renderItem).
const NativeVideoCard: React.FC<{ item: VideoItem; isActive: boolean; onInfoPress: () => void }> = ({
  item,
  isActive,
  onInfoPress,
}) => {
  const player = useVideoPlayer(item.videoUrl, (player) => {
    player.loop = true;
  });

  React.useEffect(() => {
    if (isActive) {
      player.muted = false;
      player.play();
    } else {
      player.pause();
      player.muted = true;
    }
  }, [isActive, player]);

  return (
    <View style={styles.videoContainer}>
      <View style={styles.videoWrapper}>
        <VideoView player={player} style={styles.video} nativeControls contentFit="contain" />
      </View>
      <View style={styles.videoInfo}>
        <Text style={styles.videoTitle}>{item.title}</Text>
      </View>
      <TouchableOpacity style={styles.infoButton} onPress={onInfoPress}>
        <Ionicons name="information-circle-outline" size={32} color="#fff" />
      </TouchableOpacity>
    </View>
  );
};

const VideoFeed: React.FC = () => {
  const router = useRouter();
  const [videos, setVideos] = React.useState<VideoItem[]>([]);
  const [loading, setLoading] = React.useState(true);
  const [error, setError] = React.useState<string | null>(null);
  const [activeVideoIndex, setActiveVideoIndex] = React.useState(0);

  const flatListRef = React.useRef<FlatList>(null);
  
  // Fetch videos from the backend API, filtered by the user's selected interests (if any)
  useFocusEffect(
    React.useCallback(() => {
      const loadVideos = async () => {
        try {
          setLoading(true);
          const [videosData, interests] = await Promise.all([fetchVideos(), getInterests()]);
          const allVideos: VideoItem[] = videosData ?? [];
          const filtered =
            interests && interests.length > 0
              ? allVideos.filter((video) =>
                  (video.keywords ?? []).some((kw) => interests.includes(kw))
                )
              : allVideos;
          setVideos(filtered);
          setError(null);
        } catch (err) {
          setError('Failed to load videos');
          console.error(err);
        } finally {
          setLoading(false);
        }
      };

      loadVideos();
    }, [])
  );
  
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
          <TouchableOpacity
            style={styles.infoButton}
            onPress={() => router.push(`/video/${item.id}`)}
          >
            <Ionicons name="information-circle-outline" size={32} color="#fff" />
          </TouchableOpacity>
        </View>
      );
    }

    // For native platforms, use expo-video
    return (
      <NativeVideoCard
        item={item}
        isActive={isActive}
        onInfoPress={() => router.push(`/video/${item.id}`)}
      />
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
  infoButton: {
    position: 'absolute',
    bottom: 90,
    right: 16,
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