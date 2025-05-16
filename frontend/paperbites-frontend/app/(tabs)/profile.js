import React, { useState, useEffect } from 'react';
import { View, Text, StyleSheet, FlatList, TouchableOpacity, SafeAreaView } from 'react-native';
import { useRouter } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import VideoCard from '../../components/VideoCard';
import LoadingIndicator from '../../components/LoadingIndicator';
import TopicChip from '../../components/TopicChip';
import { getFavoriteVideos, getWatchHistory } from '../../services/storage';

export default function ProfileScreen() {
  const router = useRouter();
  const [favorites, setFavorites] = useState([]);
  const [history, setHistory] = useState([]);
  const [activeTab, setActiveTab] = useState('favorites');
  const [loading, setLoading] = useState(true);

  // Load data when screen focuses
  useEffect(() => {
    loadUserData();
  }, []);

  // Function to load user data
  const loadUserData = async () => {
    setLoading(true);
    try {
      const favVideos = await getFavoriteVideos();
      const watchHistory = await getWatchHistory();
      
      setFavorites(favVideos);
      setHistory(watchHistory);
    } catch (error) {
      console.error('Error loading user data:', error);
    } finally {
      setLoading(false);
    }
  };

  // Extract favorite topics based on liked videos
  const favoriteTopics = () => {
    const topicsMap = {};
    favorites.forEach(video => {
      if (video.keywords) {
        video.keywords.forEach(keyword => {
          topicsMap[keyword] = (topicsMap[keyword] || 0) + 1;
        });
      }
    });
    
    // Convert to array and sort by count
    return Object.entries(topicsMap)
      .sort((a, b) => b[1] - a[1])
      .slice(0, 10)
      .map(item => item[0]);
  };

  // Handle video press
  const handleVideoPress = (video) => {
    router.push(`/video/${video.id}`);
  };

  // Handle topic press
  const handleTopicPress = (topic) => {
    router.push({
      pathname: '/topics',
      params: { keyword: topic }
    });
  };

  // Render tabs
  const renderTabs = () => (
    <View style={styles.tabsContainer}>
      <TouchableOpacity 
        style={[styles.tab, activeTab === 'favorites' && styles.activeTab]}
        onPress={() => setActiveTab('favorites')}
      >
        <Ionicons 
          name="heart" 
          size={18} 
          color={activeTab === 'favorites' ? '#4285F4' : '#757575'} 
        />
        <Text style={[
          styles.tabText, 
          activeTab === 'favorites' && styles.activeTabText
        ]}>
          Favorites
        </Text>
      </TouchableOpacity>
      
      <TouchableOpacity 
        style={[styles.tab, activeTab === 'history' && styles.activeTab]}
        onPress={() => setActiveTab('history')}
      >
        <Ionicons 
          name="time" 
          size={18} 
          color={activeTab === 'history' ? '#4285F4' : '#757575'} 
        />
        <Text style={[
          styles.tabText, 
          activeTab === 'history' && styles.activeTabText
        ]}>
          History
        </Text>
      </TouchableOpacity>
      
      <TouchableOpacity 
        style={[styles.tab, activeTab === 'topics' && styles.activeTab]}
        onPress={() => setActiveTab('topics')}
      >
        <Ionicons 
          name="pricetag" 
          size={18} 
          color={activeTab === 'topics' ? '#4285F4' : '#757575'} 
        />
        <Text style={[
          styles.tabText, 
          activeTab === 'topics' && styles.activeTabText
        ]}>
          Topics
        </Text>
      </TouchableOpacity>
    </View>
  );

  // Render content based on active tab
  const renderContent = () => {
    if (loading) {
      return <LoadingIndicator message="Loading your content..." />;
    }

    if (activeTab === 'favorites') {
      return favorites.length > 0 ? (
        <FlatList
          data={favorites}
          renderItem={({ item }) => (
            <VideoCard 
              video={item} 
              onPress={() => handleVideoPress(item)}
              compact={true}
            />
          )}
          keyExtractor={item => item.id}
          numColumns={2}
          contentContainerStyle={styles.gridContainer}
          columnWrapperStyle={styles.columnWrapper}
        />
      ) : (
        <View style={styles.emptyContainer}>
          <Ionicons name="heart-outline" size={60} color="#ccc" />
          <Text style={styles.emptyText}>No favorites yet</Text>
          <Text style={styles.emptySubtext}>
            Videos you like will appear here
          </Text>
          <TouchableOpacity 
            style={styles.browseButton}
            onPress={() => router.push('/feed')}
          >
            <Text style={styles.browseButtonText}>Browse Videos</Text>
          </TouchableOpacity>
        </View>
      );
    } 
    
    if (activeTab === 'history') {
      return history.length > 0 ? (
        <FlatList
          data={history}
          renderItem={({ item }) => (
            <VideoCard 
              video={item} 
              onPress={() => handleVideoPress(item)}
              compact={true}
              showWatchDate={true}
            />
          )}
          keyExtractor={item => item.id}
          numColumns={2}
          contentContainerStyle={styles.gridContainer}
          columnWrapperStyle={styles.columnWrapper}
        />
      ) : (
        <View style={styles.emptyContainer}>
          <Ionicons name="time-outline" size={60} color="#ccc" />
          <Text style={styles.emptyText}>No watch history</Text>
          <Text style={styles.emptySubtext}>
            Videos you watch will appear here
          </Text>
          <TouchableOpacity 
            style={styles.browseButton}
            onPress={() => router.push('/feed')}
          >
            <Text style={styles.browseButtonText}>Browse Videos</Text>
          </TouchableOpacity>
        </View>
      );
    } 
    
    // Topics tab
    const topics = favoriteTopics();
    return topics.length > 0 ? (
      <View style={styles.topicsContainer}>
        <Text style={styles.topicsTitle}>Your Favorite Topics</Text>
        <View style={styles.topicsGrid}>
          {topics.map(topic => (
            <TopicChip
              key={topic}
              topic={topic}
              onPress={() => handleTopicPress(topic)}
            />
          ))}
        </View>
      </View>
    ) : (
      <View style={styles.emptyContainer}>
        <Ionicons name="pricetag-outline" size={60} color="#ccc" />
        <Text style={styles.emptyText}>No favorite topics yet</Text>
        <Text style={styles.emptySubtext}>
          Like videos to discover your interests
        </Text>
        <TouchableOpacity 
          style={styles.browseButton}
          onPress={() => router.push('/topics')}
        >
          <Text style={styles.browseButtonText}>Browse Topics</Text>
        </TouchableOpacity>
      </View>
    );
  };

  return (
    <SafeAreaView style={styles.container}>
      <View style={styles.header}>
        <Text style={styles.headerTitle}>Your Profile</Text>
        <TouchableOpacity 
          style={styles.refreshButton}
          onPress={loadUserData}
        >
          <Ionicons name="refresh" size={22} color="#333" />
        </TouchableOpacity>
      </View>
      
      {renderTabs()}
      {renderContent()}
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#fff',
  },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingHorizontal: 16,
    paddingVertical: 16,
    borderBottomWidth: 1,
    borderBottomColor: '#e0e0e0',
  },
  headerTitle: {
    fontSize: 20,
    fontWeight: 'bold',
    color: '#333',
  },
  refreshButton: {
    padding: 8,
  },
  tabsContainer: {
    flexDirection: 'row',
    borderBottomWidth: 1,
    borderBottomColor: '#e0e0e0',
  },
  tab: {
    flex: 1,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    paddingVertical: 12,
  },
  activeTab: {
    borderBottomWidth: 2,
    borderBottomColor: '#4285F4',
  },
  tabText: {
    fontSize: 14,
    color: '#757575',
    marginLeft: 4,
  },
  activeTabText: {
    color: '#4285F4',
    fontWeight: '600',
  },
  gridContainer: {
    padding: 8,
  },
  columnWrapper: {
    justifyContent: 'space-between',
  },
  emptyContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    padding: 20,
  },
  emptyText: {
    fontSize: 18,
    fontWeight: 'bold',
    color: '#333',
    marginTop: 12,
  },
  emptySubtext: {
    fontSize: 14,
    color: '#757575',
    marginTop: 8,
    textAlign: 'center',
  },
  browseButton: {
    marginTop: 20,
    backgroundColor: '#4285F4',
    paddingHorizontal: 20,
    paddingVertical: 10,
    borderRadius: 8,
  },
  browseButtonText: {
    color: '#fff',
    fontWeight: 'bold',
  },
  topicsContainer: {
    padding: 16,
  },
  topicsTitle: {
    fontSize: 18,
    fontWeight: 'bold',
    color: '#333',
    marginBottom: 16,
  },
  topicsGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
  },
});