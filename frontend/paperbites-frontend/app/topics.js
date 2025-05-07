import React, { useState, useEffect } from 'react';
import { 
  View, 
  Text, 
  FlatList, 
  StyleSheet, 
  TouchableOpacity, 
  SafeAreaView
} from 'react-native';
import { useLocalSearchParams, useRouter } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import VideoCard from '../components/VideoCard';
import TopicChip from '../components/TopicChip';
import LoadingIndicator from '../components/LoadingIndicator';
import ErrorMessage from '../components/ErrorMessage';
import { fetchTopics, fetchVideos } from '../services/api';
import Colors from '../constants/Colors';

export default function TopicsScreen() {
  const router = useRouter();
  const params = useLocalSearchParams();
  const initialKeyword = params?.keyword;
  
  const [topics, setTopics] = useState([]);
  const [selectedTopic, setSelectedTopic] = useState(initialKeyword || null);
  const [videos, setVideos] = useState([]);
  const [loading, setLoading] = useState(true);
  const [videosLoading, setVideosLoading] = useState(false);
  const [error, setError] = useState(null);

  // Load topics
  useEffect(() => {
    const loadTopics = async () => {
      try {
        setLoading(true);
        const fetchedTopics = await fetchTopics();
        setTopics(fetchedTopics);
        
        // If no topic is selected yet, select the first one
        if (!selectedTopic && fetchedTopics.length > 0 && !initialKeyword) {
          setSelectedTopic(fetchedTopics[0]);
        }
      } catch (err) {
        setError(`Failed to load topics: ${err.message}`);
      } finally {
        setLoading(false);
      }
    };

    loadTopics();
  }, []);

  // Load videos for selected topic
  useEffect(() => {
    if (!selectedTopic) return;

    const loadTopicVideos = async () => {
      try {
        setVideosLoading(true);
        const fetchedVideos = await fetchVideos({
          keyword: selectedTopic,
          limit: 50,
        });
        setVideos(fetchedVideos);
      } catch (err) {
        console.error(`Failed to load videos for topic ${selectedTopic}:`, err);
        setVideos([]);
      } finally {
        setVideosLoading(false);
      }
    };

    loadTopicVideos();
  }, [selectedTopic]);

  // Handle topic selection
  const handleTopicPress = (topic) => {
    setSelectedTopic(topic);
  };

  // Handle video selection
  const handleVideoPress = (video) => {
    router.push(`/video/${video.id}`);
  };

  // Render topic item
  const renderTopicItem = ({ item }) => (
    <TopicChip
      topic={item}
      selected={selectedTopic === item}
      onPress={handleTopicPress}
    />
  );

  if (loading) {
    return <LoadingIndicator message="Loading topics..." />;
  }

  if (error) {
    return (
      <ErrorMessage 
        message={error} 
        onRetry={() => router.replace('/topics')}
        onBack={() => router.back()}
      />
    );
  }

  return (
    <SafeAreaView style={styles.container}>
      {/* Header */}
      <View style={styles.header}>
        <Text style={styles.headerTitle}>Browse by Topic</Text>
      </View>

      {/* Topics horizontal list */}
      <View style={styles.topicsContainer}>
        <FlatList
          data={topics}
          renderItem={renderTopicItem}
          keyExtractor={(item) => item}
          horizontal
          showsHorizontalScrollIndicator={false}
          contentContainerStyle={styles.topicsList}
        />
      </View>

      {/* Videos for selected topic */}
      <View style={styles.videosContainer}>
        {selectedTopic ? (
          <Text style={styles.selectedTopicTitle}>
            Videos about "{selectedTopic}"
          </Text>
        ) : (
          <Text style={styles.selectedTopicTitle}>
            Select a topic to view videos
          </Text>
        )}

        {videosLoading ? (
          <LoadingIndicator message="Loading videos..." />
        ) : videos.length === 0 ? (
          <View style={styles.centerContainer}>
            <Text style={styles.emptyText}>
              No videos found for this topic
            </Text>
          </View>
        ) : (
          <FlatList
            data={videos}
            renderItem={({ item }) => (
              <VideoCard video={item} onPress={handleVideoPress} />
            )}
            keyExtractor={(item) => item.id}
            showsVerticalScrollIndicator={false}
            contentContainerStyle={styles.videosList}
          />
        )}
      </View>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#f9f9f9',
  },
  centerContainer: {
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
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    paddingHorizontal: 15,
    paddingVertical: 10,
    borderBottomWidth: 1,
    borderBottomColor: '#e0e0e0',
    backgroundColor: '#fff',
  },
  headerTitle: {
    fontSize: 18,
    fontWeight: 'bold',
    color: '#333',
  },
  topicsContainer: {
    borderBottomWidth: 1,
    borderBottomColor: '#e0e0e0',
    backgroundColor: '#fff',
  },
  topicsList: {
    paddingHorizontal: 15,
    paddingVertical: 12,
  },
  videosContainer: {
    flex: 1,
  },
  selectedTopicTitle: {
    fontSize: 16,
    fontWeight: 'bold',
    color: '#333',
    padding: 15,
    paddingBottom: 5,
  },
  videosList: {
    paddingVertical: 10,
  },
});