// hooks/useStorage.js
import { useState, useEffect, useCallback } from 'react';
import AsyncStorage from '@react-native-async-storage/async-storage';

// Constants for storage keys
const STORAGE_KEYS = {
  RECENT_SEARCHES: 'paperbites_recent_searches',
  FAVORITE_VIDEOS: 'paperbites_favorite_videos',
  WATCH_HISTORY: 'paperbites_watch_history',
  APP_SETTINGS: 'paperbites_app_settings',
};

/**
 * Custom hook for managing favorite videos
 * 
 * @returns {Object} - Favorite videos data and functions
 */
export const useFavoriteVideos = () => {
  const [favorites, setFavorites] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Load favorites on mount
  useEffect(() => {
    const loadFavorites = async () => {
      try {
        setLoading(true);
        const jsonValue = await AsyncStorage.getItem(STORAGE_KEYS.FAVORITE_VIDEOS);
        const favs = jsonValue != null ? JSON.parse(jsonValue) : [];
        setFavorites(favs);
      } catch (err) {
        console.error('Error loading favorites:', err);
        setError('Failed to load favorite videos');
      } finally {
        setLoading(false);
      }
    };

    loadFavorites();
  }, []);

  // Check if a video is in favorites
  const isFavorite = useCallback((videoId) => {
    return favorites.some(video => video.id === videoId);
  }, [favorites]);

  // Add a video to favorites
  const addFavorite = useCallback(async (video) => {
    if (!video || !video.id) return false;
    
    try {
      // Check if already favorited
      if (isFavorite(video.id)) return true;
      
      // Add to favorites
      const updatedFavorites = [video, ...favorites];
      setFavorites(updatedFavorites);
      
      // Save to storage
      const jsonValue = JSON.stringify(updatedFavorites);
      await AsyncStorage.setItem(STORAGE_KEYS.FAVORITE_VIDEOS, jsonValue);
      
      return true;
    } catch (err) {
      console.error('Error adding favorite:', err);
      return false;
    }
  }, [favorites, isFavorite]);

  // Remove a video from favorites
  const removeFavorite = useCallback(async (videoId) => {
    try {
      // Filter out the video to remove
      const updatedFavorites = favorites.filter(video => video.id !== videoId);
      setFavorites(updatedFavorites);
      
      // Save to storage
      const jsonValue = JSON.stringify(updatedFavorites);
      await AsyncStorage.setItem(STORAGE_KEYS.FAVORITE_VIDEOS, jsonValue);
      
      return false; // Return false to indicate it's no longer a favorite
    } catch (err) {
      console.error('Error removing favorite:', err);
      return true; // If error, assume it's still a favorite
    }
  }, [favorites]);

  // Toggle favorite status
  const toggleFavorite = useCallback(async (video) => {
    if (!video || !video.id) return isFavorite(video?.id || '');
    
    if (isFavorite(video.id)) {
      const result = await removeFavorite(video.id);
      return result;
    } else {
      const result = await addFavorite(video);
      return result;
    }
  }, [isFavorite, removeFavorite, addFavorite]);

  return {
    favorites,
    loading,
    error,
    isFavorite,
    addFavorite,
    removeFavorite,
    toggleFavorite,
  };
};
