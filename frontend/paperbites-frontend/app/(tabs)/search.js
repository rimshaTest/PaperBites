import React, { useState, useEffect } from 'react';
import { 
  View, 
  Text, 
  TextInput, 
  FlatList, 
  StyleSheet, 
  TouchableOpacity, 
  Keyboard,
  SafeAreaView
} from 'react-native';
import { useRouter } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import FullscreenFeed from '../../components/FullscreenFeed';
import LoadingIndicator from '../../components/LoadingIndicator';
import { fetchVideos } from '../../services/api';
import { saveRecentSearches, getRecentSearches } from '../../services/storage';

export default function SearchScreen() {
  const router = useRouter();
  const [searchQuery, setSearchQuery] = useState('');
  const [videos, setVideos] = useState([]);
  const [loading, setLoading] = useState(false);
  const [searchPerformed, setSearchPerformed] = useState(false);
  const [recentSearches, setRecentSearches] = useState([]);
  const [showFullscreen, setShowFullscreen] = useState(false);

  // Load recent searches from storage
  useEffect(() => {
    const loadRecentSearches = async () => {
      const searches = await getRecentSearches();
      setRecentSearches(searches);
    };
    
    loadRecentSearches();
  }, []);

  // Handle search submission
  const handleSearch = async () => {
    if (!searchQuery.trim()) return;
    
    Keyboard.dismiss();
    setLoading(true);
    setSearchPerformed(true);
    
    try {
      const results = await fetchVideos({
        keyword: searchQuery,
        limit: 50,
      });
      setVideos(results);
      
      // Add to recent searches if not already there
      if (!recentSearches.includes(searchQuery)) {
        const updatedSearches = [searchQuery, ...recentSearches].slice(0, 5);
        setRecentSearches(updatedSearches);
        saveRecentSearches(updatedSearches);
      }
      
      // If videos found, show fullscreen feed directly
      if (results.length > 0) {
        setShowFullscreen(true);
      }
    } catch (error) {
      console.error('Search error:', error);
      setVideos([]);
    } finally {
      setLoading(false);
    }
  };

  // Clear search
  const clearSearch = () => {
    setSearchQuery('');
    setVideos([]);
    setSearchPerformed(false);
    setShowFullscreen(false);
  };

  // Handle recent search tap
  const handleRecentSearchTap = (query) => {
    setSearchQuery(query);
    
    // Automatically search after a short delay
    setTimeout(() => {
      handleSearch();
    }, 100);
  };

  // Handle back button press to return to search screen
  const handleBackFromFullscreen = () => {
    setShowFullscreen(false);
  };

  // Render recent search item
  const renderRecentSearchItem = ({ item }) => (
    <TouchableOpacity 
      style={styles.recentSearchItem}
      onPress={() => handleRecentSearchTap(item)}
    >
      <Ionicons name="time-outline" size={16} color="#666" />
      <Text style={styles.recentSearchText}>{item}</Text>
    </TouchableOpacity>
  );

  // If showing fullscreen feed, render it
  if (showFullscreen) {
    return (
      <View style={styles.fullscreenContainer}>
        <FullscreenFeed 
          initialVideos={videos} 
          onBackPress={handleBackFromFullscreen}
        />
      </View>
    );
  }

  return (
    <SafeAreaView style={styles.container}>
      {/* Search header */}
      <View style={styles.searchHeader}>
        <View style={styles.searchInputContainer}>
          <Ionicons name="search" size={20} color="#666" style={styles.searchIcon} />
          <TextInput
            style={styles.searchInput}
            placeholder="Search research papers..."
            value={searchQuery}
            onChangeText={setSearchQuery}
            onSubmitEditing={handleSearch}
            returnKeyType="search"
            autoCapitalize="none"
          />
          {searchQuery.length > 0 && (
            <TouchableOpacity onPress={clearSearch} style={styles.clearButton}>
              <Ionicons name="close-circle" size={20} color="#666" />
            </TouchableOpacity>
          )}
        </View>
        
        <TouchableOpacity style={styles.searchButton} onPress={handleSearch}>
          <Text style={styles.searchButtonText}>Search</Text>
        </TouchableOpacity>
      </View>

      {/* Content area */}
      <View style={styles.contentContainer}>
        {loading ? (
          <LoadingIndicator message="Searching videos..." />
        ) : searchPerformed ? (
          videos.length > 0 ? (
            // This should never show because we go straight to fullscreen if videos found
            <View style={styles.centerContainer}>
              <Text style={styles.foundResultsText}>
                Found {videos.length} videos for "{searchQuery}"
              </Text>
              <TouchableOpacity
                style={styles.watchButton}
                onPress={() => setShowFullscreen(true)}
              >
                <Ionicons name="play-circle" size={24} color="#fff" />
                <Text style={styles.watchButtonText}>Watch Now</Text>
              </TouchableOpacity>
            </View>
          ) : (
            <View style={styles.centerContainer}>
              <Text style={styles.noResultsText}>
                No videos found for "{searchQuery}"
              </Text>
              <Text style={styles.suggestionsText}>
                Try using different keywords or browse by topic
              </Text>
              <TouchableOpacity
                style={styles.browseButton}
                onPress={() => router.push('/topics')}
              >
                <Text style={styles.browseButtonText}>Browse Topics</Text>
              </TouchableOpacity>
            </View>
          )
        ) : (
          // Show recent searches when not searching
          <View style={styles.recentSearchesContainer}>
            <Text style={styles.recentSearchesTitle}>Recent Searches</Text>
            <FlatList
              data={recentSearches}
              renderItem={renderRecentSearchItem}
              keyExtractor={(item) => item}
              showsVerticalScrollIndicator={false}
              ItemSeparatorComponent={() => <View style={styles.separator} />}
              ListEmptyComponent={
                <Text style={styles.emptyText}>No recent searches</Text>
              }
            />
          </View>
        )}
      </View>
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
  searchHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    padding: 15,
    borderBottomWidth: 1,
    borderBottomColor: '#e0e0e0',
  },
  searchInputContainer: {
    flex: 1,
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#f2f2f2',
    borderRadius: 10,
    paddingHorizontal: 10,
    height: 40,
  },
  searchIcon: {
    marginRight: 5,
  },
  searchInput: {
    flex: 1,
    height: 40,
    fontSize: 16,
  },
  clearButton: {
    padding: 5,
  },
  searchButton: {
    marginLeft: 10,
    backgroundColor: '#4285F4',
    paddingHorizontal: 15,
    paddingVertical: 10,
    borderRadius: 5,
  },
  searchButtonText: {
    color: '#fff',
    fontWeight: 'bold',
    fontSize: 14,
  },
  contentContainer: {
    flex: 1,
  },
  centerContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    padding: 20,
  },
  foundResultsText: {
    fontSize: 16,
    fontWeight: 'bold',
    color: '#333',
    marginBottom: 20,
    textAlign: 'center',
  },
  watchButton: {
    flexDirection: 'row',
    backgroundColor: '#4285F4',
    paddingHorizontal: 20,
    paddingVertical: 12,
    borderRadius: 25,
    alignItems: 'center',
  },
  watchButtonText: {
    color: '#fff',
    fontSize: 16,
    fontWeight: 'bold',
    marginLeft: 8,
  },
  noResultsText: {
    fontSize: 16,
    fontWeight: 'bold',
    color: '#333',
    marginBottom: 10,
    textAlign: 'center',
  },
  suggestionsText: {
    fontSize: 14,
    color: '#666',
    marginBottom: 20,
    textAlign: 'center',
  },
  browseButton: {
    backgroundColor: '#4285F4',
    paddingHorizontal: 15,
    paddingVertical: 10,
    borderRadius: 5,
  },
  browseButtonText: {
    color: '#fff',
    fontSize: 14,
  },
  recentSearchesContainer: {
    padding: 15,
  },
  recentSearchesTitle: {
    fontSize: 16,
    fontWeight: 'bold',
    color: '#333',
    marginBottom: 15,
  },
  recentSearchItem: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingVertical: 12,
  },
  recentSearchText: {
    fontSize: 16,
    color: '#333',
    marginLeft: 10,
  },
  separator: {
    height: 1,
    backgroundColor: '#e0e0e0',
  },
  emptyText: {
    fontSize: 14,
    color: '#666',
    fontStyle: 'italic',
    textAlign: 'center',
    marginTop: 20,
  },
});