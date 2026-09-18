import React, { useCallback } from 'react';
import {
  View,
  Text,
  FlatList,
  StyleSheet,
  TouchableOpacity,
  SafeAreaView
} from 'react-native';
import { useRouter, useFocusEffect } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import VideoCard from '../components/VideoCard';
import { useFavoriteVideos } from '../hooks/useStorage';
import Colors from '../constants/Colors';

export default function SavedScreen() {
  const router = useRouter();
  const { favorites, loading, isFavorite, toggleFavorite, removeFavorite } = useFavoriteVideos();

  // Bookmarks are stored locally, so re-check them whenever this screen regains focus
  // (e.g. after bookmarking something from the feed and coming back).
  useFocusEffect(
    useCallback(() => {
      // useFavoriteVideos reloads from storage on mount; nothing else needed here yet,
      // but this hook is the seam for a future server-backed refetch.
    }, [])
  );

  const handleVideoPress = (video) => {
    router.push(`/video/${video.id}`);
  };

  return (
    <SafeAreaView style={styles.container}>
      <View style={styles.header}>
        <TouchableOpacity onPress={() => router.back()} style={styles.headerButton}>
          <Ionicons name="arrow-back" size={24} color="#333" />
        </TouchableOpacity>
        <Text style={styles.headerTitle}>Saved</Text>
        <View style={styles.headerButton} />
      </View>

      {loading ? (
        <View style={styles.centerContainer}>
          <Text style={styles.emptyText}>Loading saved papers...</Text>
        </View>
      ) : favorites.length === 0 ? (
        <View style={styles.centerContainer}>
          <Ionicons name="bookmark-outline" size={40} color="#ccc" />
          <Text style={styles.emptyText}>
            Nothing saved yet. Tap the bookmark icon on any paper to keep it here.
          </Text>
        </View>
      ) : (
        <FlatList
          data={favorites}
          renderItem={({ item }) => (
            <VideoCard
              video={item}
              onPress={handleVideoPress}
              isBookmarked={isFavorite(item.id)}
              onToggleBookmark={() => removeFavorite(item.id)}
            />
          )}
          keyExtractor={(item) => item.id}
          showsVerticalScrollIndicator={false}
          contentContainerStyle={styles.videosList}
        />
      )}
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#f9f9f9',
  },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingHorizontal: 10,
    paddingVertical: 10,
    borderBottomWidth: 1,
    borderBottomColor: '#e0e0e0',
    backgroundColor: '#fff',
  },
  headerButton: {
    width: 34,
    padding: 5,
  },
  headerTitle: {
    fontSize: 18,
    fontWeight: 'bold',
    color: '#333',
  },
  centerContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    padding: 30,
  },
  emptyText: {
    fontSize: 15,
    color: '#666',
    textAlign: 'center',
    marginTop: 10,
  },
  videosList: {
    paddingVertical: 10,
  },
});
