import React from 'react';
import {
  View,
  Text,
  FlatList,
  StyleSheet,
  TouchableOpacity,
  SafeAreaView
} from 'react-native';
import { useRouter } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import VideoCard from '../components/VideoCard';
import { useFavoriteVideos } from '../hooks/useStorage';
import { useAuth } from '../hooks/useAuth';
import Colors from '../constants/Colors';

export default function SavedScreen() {
  const router = useRouter();
  const { user, token, loading: authLoading } = useAuth();
  const { favorites, loading, isFavorite, removeFavorite } = useFavoriteVideos(token);

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

      {authLoading || loading ? (
        <View style={styles.centerContainer}>
          <Text style={styles.emptyText}>Loading saved papers...</Text>
        </View>
      ) : !user ? (
        <View style={styles.centerContainer}>
          <Ionicons name="lock-closed-outline" size={40} color="#ccc" />
          <Text style={styles.emptyText}>Log in to see your saved papers.</Text>
          <TouchableOpacity style={styles.loginButton} onPress={() => router.push('/login')}>
            <Text style={styles.loginButtonText}>Log In</Text>
          </TouchableOpacity>
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
  loginButton: {
    backgroundColor: '#4285F4',
    borderRadius: 8,
    paddingVertical: 10,
    paddingHorizontal: 30,
    marginTop: 16,
  },
  loginButtonText: {
    color: '#fff',
    fontSize: 15,
    fontWeight: 'bold',
  },
  videosList: {
    paddingVertical: 10,
  },
});
