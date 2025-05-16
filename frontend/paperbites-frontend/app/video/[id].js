import React, { useState, useEffect } from 'react';
import { 
  View, 
  Text, 
  StyleSheet, 
  ScrollView, 
  TouchableOpacity,
  Share,
  SafeAreaView
} from 'react-native';
import { useLocalSearchParams, useRouter } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import FullscreenFeed from '../../components/FullscreenFeed';
import LoadingIndicator from '../../components/LoadingIndicator';
import ErrorMessage from '../../components/ErrorMessage';
import { fetchVideoById } from '../../services/api';
import { addToWatchHistory, isVideoFavorited, addFavoriteVideo, removeFavoriteVideo } from '../../services/storage';

export default function VideoDetailScreen() {
  const router = useRouter();
  const { id } = useLocalSearchParams();
  const [video, setVideo] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [showDetails, setShowDetails] = useState(false);
  const [isFavorite, setIsFavorite] = useState(false);

  // Load video data
  useEffect(() => {
    const loadVideo = async () => {
      try {
        setLoading(true);
        const data = await fetchVideoById(id);
        setVideo(data);
        
        // Add to watch history
        if (data) {
          addToWatchHistory(data);
        }
        
        // Check if video is favorited
        const favorited = await isVideoFavorited(id);
        setIsFavorite(favorited);
      } catch (err) {
        setError(`Failed to load video: ${err.message}`);
      } finally {
        setLoading(false);
      }
    };

    if (id) {
      loadVideo();
    }
  }, [id]);

  // Toggle favorite status
  const toggleFavorite = async () => {
    if (isFavorite) {
      await removeFavoriteVideo(id);
    } else {
      if (video) {
        await addFavoriteVideo(video);
      }
    }
    setIsFavorite(!isFavorite);
  };

  // Share video
  const handleShare = async () => {
    if (!video) return;

    try {
      await Share.share({
        message: `Check out this research video: ${video.title}\n${video.videoUrl}`,
        title: video.title,
      });
    } catch (error) {
      console.error('Error sharing video:', error);
    }
  };

  // Toggle between video and details
  const toggleDetails = () => {
    setShowDetails(!showDetails);
  };

  if (loading) {
    return <LoadingIndicator message="Loading video..." />;
  }

  if (error || !video) {
    return (
      <ErrorMessage 
        message={error || 'Video not found'} 
        onBack={() => router.back()}
      />
    );
  }

  // If showing fullscreen video (default view)
  if (!showDetails) {
    return (
      <View style={styles.fullscreenContainer}>
        {/* Button to toggle to details view */}
        <SafeAreaView style={styles.detailsButtonContainer}>
          <TouchableOpacity style={styles.detailsButton} onPress={toggleDetails}>
            <Ionicons name="information-circle" size={22} color="#fff" />
            <Text style={styles.detailsButtonText}>Details</Text>
          </TouchableOpacity>
        </SafeAreaView>
        
        <FullscreenFeed initialVideoId={id} />
      </View>
    );
  }

  // If showing details view
  return (
    <SafeAreaView style={styles.container}>
      {/* Header with back button and share */}
      <View style={styles.header}>
        <TouchableOpacity onPress={toggleDetails} style={styles.headerButton}>
          <Ionicons name="arrow-back" size={24} color="#333" />
        </TouchableOpacity>
        
        <Text style={styles.headerTitle} numberOfLines={1}>
          Video Details
        </Text>
        
        <View style={styles.headerActions}>
          <TouchableOpacity onPress={toggleFavorite} style={styles.headerButton}>
            <Ionicons 
              name={isFavorite ? "heart" : "heart-outline"} 
              size={24} 
              color={isFavorite ? "#E53935" : "#333"} 
            />
          </TouchableOpacity>
          
          <TouchableOpacity onPress={handleShare} style={styles.headerButton}>
            <Ionicons name="share-outline" size={24} color="#333" />
          </TouchableOpacity>
        </View>
      </View>

      {/* Video details */}
      <ScrollView style={styles.detailsContainer}>
        <Text style={styles.title}>{video.title}</Text>
        
        {/* DOI if available */}
        {video.doi && (
          <View style={styles.infoRow}>
            <Ionicons name="link-outline" size={16} color="#666" />
            <Text style={styles.infoText}>DOI: {video.doi}</Text>
          </View>
        )}

        {/* Summary */}
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>Summary</Text>
          <Text style={styles.summary}>{video.summary}</Text>
        </View>

        {/* Key insights */}
        {video.key_insights && video.key_insights.length > 0 && (
          <View style={styles.section}>
            <Text style={styles.sectionTitle}>Key Insights</Text>
            {video.key_insights.map((insight, index) => (
              <View key={index} style={styles.insightItem}>
                <Text style={styles.insightBullet}>•</Text>
                <Text style={styles.insightText}>{insight}</Text>
              </View>
            ))}
          </View>
        )}

        {/* Keywords/topics */}
        {video.keywords && video.keywords.length > 0 && (
          <View style={styles.section}>
            <Text style={styles.sectionTitle}>Topics</Text>
            <View style={styles.keywordsContainer}>
              {video.keywords.map((keyword, index) => (
                <TouchableOpacity 
                  key={index} 
                  style={styles.keywordChip}
                  onPress={() => router.push({
                    pathname: '/topics',
                    params: { keyword }
                  })}
                >
                  <Text style={styles.keywordText}>{keyword}</Text>
                </TouchableOpacity>
              ))}
            </View>
          </View>
        )}
        
        {/* Hashtags */}
        {video.hashtags && (
          <View style={styles.section}>
            <Text style={styles.hashtags}>{video.hashtags}</Text>
          </View>
        )}
        
        {/* Return to video button */}
        <TouchableOpacity 
          style={styles.watchButton}
          onPress={toggleDetails}
        >
          <Ionicons name="play-circle" size={24} color="#fff" />
          <Text style={styles.watchButtonText}>Return to Video</Text>
        </TouchableOpacity>
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#fff',
  },
  fullscreenContainer: {
    flex: 1,
    backgroundColor: '#000',
  },
  detailsButtonContainer: {
    position: 'absolute',
    bottom: 20,
    right: 20,
    zIndex: 100,
  },
  detailsButton: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: 'rgba(0, 0, 0, 0.5)',
    paddingHorizontal: 12,
    paddingVertical: 8,
    borderRadius: 20,
  },
  detailsButtonText: {
    color: '#fff',
    fontSize: 14,
    marginLeft: 6,
  },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 10,
    paddingVertical: 10,
    borderBottomWidth: 1,
    borderBottomColor: '#e0e0e0',
  },
  headerButton: {
    padding: 5,
    borderRadius: 20,
  },
  headerTitle: {
    flex: 1,
    fontSize: 16,
    fontWeight: 'bold',
    textAlign: 'center',
    marginHorizontal: 10,
  },
  headerActions: {
    flexDirection: 'row',
  },
  detailsContainer: {
    flex: 1,
    padding: 15,
  },
  title: {
    fontSize: 20,
    fontWeight: 'bold',
    marginBottom: 10,
    color: '#333',
  },
  infoRow: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 15,
  },
  infoText: {
    fontSize: 14,
    color: '#666',
    marginLeft: 5,
  },
  section: {
    marginBottom: 20,
  },
  sectionTitle: {
    fontSize: 16,
    fontWeight: 'bold',
    marginBottom: 8,
    color: '#333',
  },
  summary: {
    fontSize: 14,
    lineHeight: 20,
    color: '#333',
  },
  insightItem: {
    flexDirection: 'row',
    marginBottom: 5,
    paddingLeft: 5,
  },
  insightBullet: {
    fontSize: 14,
    marginRight: 8,
    color: '#4285F4',
  },
  insightText: {
    flex: 1,
    fontSize: 14,
    lineHeight: 20,
    color: '#333',
  },
  keywordsContainer: {
    flexDirection: 'row',
    flexWrap: 'wrap',
  },
  keywordChip: {
    backgroundColor: '#f0f0f0',
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: 16,
    marginRight: 8,
    marginBottom: 8,
  },
  keywordText: {
    fontSize: 14,
    color: '#4285F4',
  },
  hashtags: {
    fontSize: 14,
    color: '#4285F4',
    lineHeight: 20,
  },
  watchButton: {
    flexDirection: 'row',
    backgroundColor: '#4285F4',
    paddingVertical: 12,
    paddingHorizontal: 20,
    borderRadius: 25,
    alignItems: 'center',
    justifyContent: 'center',
    marginTop: 10,
    marginBottom: 30,
  },
  watchButtonText: {
    color: '#fff',
    fontSize: 16,
    fontWeight: 'bold',
    marginLeft: 8,
  },
});