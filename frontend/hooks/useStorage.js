import { useState, useEffect, useCallback } from 'react';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { fetchBookmarks, addBookmark, removeBookmark } from '../services/api';

// Constants for storage keys
const STORAGE_KEYS = {
  RECENT_SEARCHES: 'paperbites_recent_searches',
  WATCH_HISTORY: 'paperbites_watch_history',
  APP_SETTINGS: 'paperbites_app_settings',
};

/**
 * Custom hook for managing recent searches
 * 
 * @returns {Object} - Recent searches data and functions
 */
export const useRecentSearches = () => {
  const [recentSearches, setRecentSearches] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Load recent searches on mount
  useEffect(() => {
    const loadRecentSearches = async () => {
      try {
        setLoading(true);
        const jsonValue = await AsyncStorage.getItem(STORAGE_KEYS.RECENT_SEARCHES);
        const searches = jsonValue != null ? JSON.parse(jsonValue) : [];
        setRecentSearches(searches);
      } catch (err) {
        console.error('Error loading recent searches:', err);
        setError('Failed to load recent searches');
      } finally {
        setLoading(false);
      }
    };

    loadRecentSearches();
  }, []);

  // Add a search term to recent searches
  const addRecentSearch = useCallback(async (searchTerm) => {
    if (!searchTerm.trim()) return;
    
    try {
      // Remove if already exists to avoid duplicates
      const filteredSearches = recentSearches.filter(term => term !== searchTerm);
      
      // Add to beginning of list
      const updatedSearches = [searchTerm, ...filteredSearches].slice(0, 10);
      
      // Update state
      setRecentSearches(updatedSearches);
      
      // Save to storage
      const jsonValue = JSON.stringify(updatedSearches);
      await AsyncStorage.setItem(STORAGE_KEYS.RECENT_SEARCHES, jsonValue);
      
      return true;
    } catch (err) {
      console.error('Error adding recent search:', err);
      return false;
    }
  }, [recentSearches]);

  // Clear all recent searches
  const clearRecentSearches = useCallback(async () => {
    try {
      await AsyncStorage.setItem(STORAGE_KEYS.RECENT_SEARCHES, JSON.stringify([]));
      setRecentSearches([]);
      return true;
    } catch (err) {
      console.error('Error clearing recent searches:', err);
      return false;
    }
  }, []);

  return {
    recentSearches,
    loading,
    error,
    addRecentSearch,
    clearRecentSearches,
  };
};

/**
 * Custom hook for managing bookmarked ("favorite") videos.
 *
 * Bookmarks are stored server-side (see backend/bookmarks.py) and scoped to
 * the signed-in account, so a session token (from useAuth()) is required.
 * With no token, this hook simply reports an empty, non-loading list rather
 * than calling the API - callers should route to /login if they want to let
 * a signed-out user bookmark something.
 *
 * @param {string|null} token - Session token from useAuth()
 * @returns {Object} - Favorite videos data and functions
 */
export const useFavoriteVideos = (token) => {
  const [favorites, setFavorites] = useState([]);
  const [loading, setLoading] = useState(!!token);
  const [error, setError] = useState(null);

  // (Re)load bookmarks whenever the session token changes (login/logout)
  useEffect(() => {
    let cancelled = false;

    if (!token) {
      setFavorites([]);
      setLoading(false);
      return;
    }

    const load = async () => {
      try {
        setLoading(true);
        const bookmarked = await fetchBookmarks(token);
        if (!cancelled) setFavorites(bookmarked);
      } catch (err) {
        console.error('Error loading favorites:', err);
        if (!cancelled) setError('Failed to load favorite videos');
      } finally {
        if (!cancelled) setLoading(false);
      }
    };

    load();
    return () => { cancelled = true; };
  }, [token]);

  // Check if a video is in favorites
  const isFavorite = useCallback((videoId) => {
    return favorites.some(video => video.id === videoId);
  }, [favorites]);

  // Add a video to favorites
  const addFavorite = useCallback(async (video) => {
    if (!video || !video.id || !token) return false;
    if (isFavorite(video.id)) return true;

    // Optimistic update so the UI reacts immediately
    setFavorites(prev => [video, ...prev]);

    try {
      await addBookmark(token, video.id);
      return true;
    } catch (err) {
      console.error('Error adding favorite:', err);
      // Roll back on failure
      setFavorites(prev => prev.filter(v => v.id !== video.id));
      return false;
    }
  }, [token, isFavorite]);

  // Remove a video from favorites
  const removeFavorite = useCallback(async (videoId) => {
    if (!token) return false;

    const previous = favorites;
    setFavorites(prev => prev.filter(video => video.id !== videoId));

    try {
      await removeBookmark(token, videoId);
      return true;
    } catch (err) {
      console.error('Error removing favorite:', err);
      // Roll back on failure
      setFavorites(previous);
      return false;
    }
  }, [token, favorites]);

  // Toggle favorite status
  const toggleFavorite = useCallback(async (video) => {
    if (isFavorite(video.id)) {
      return removeFavorite(video.id);
    } else {
      return addFavorite(video);
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

/**
 * Custom hook for managing watch history
 * 
 * @returns {Object} - Watch history data and functions
 */
export const useWatchHistory = () => {
  const [history, setHistory] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Load watch history on mount
  useEffect(() => {
    const loadHistory = async () => {
      try {
        setLoading(true);
        const jsonValue = await AsyncStorage.getItem(STORAGE_KEYS.WATCH_HISTORY);
        const hist = jsonValue != null ? JSON.parse(jsonValue) : [];
        setHistory(hist);
      } catch (err) {
        console.error('Error loading watch history:', err);
        setError('Failed to load watch history');
      } finally {
        setLoading(false);
      }
    };

    loadHistory();
  }, []);

  // Add a video to watch history
  const addToHistory = useCallback(async (video) => {
    if (!video || !video.id) return false;
    
    try {
      // Remove if already in history to avoid duplicates
      const filteredHistory = history.filter(item => item.id !== video.id);
      
      // Add to beginning of history with timestamp
      const updatedHistory = [
        { ...video, watchedAt: Date.now() },
        ...filteredHistory
      ];
      
      // Limit history to 50 items
      const limitedHistory = updatedHistory.slice(0, 50);
      
      // Update state
      setHistory(limitedHistory);
      
      // Save to storage
      const jsonValue = JSON.stringify(limitedHistory);
      await AsyncStorage.setItem(STORAGE_KEYS.WATCH_HISTORY, jsonValue);
      
      return true;
    } catch (err) {
      console.error('Error adding to watch history:', err);
      return false;
    }
  }, [history]);

  // Clear watch history
  const clearHistory = useCallback(async () => {
    try {
      await AsyncStorage.setItem(STORAGE_KEYS.WATCH_HISTORY, JSON.stringify([]));
      setHistory([]);
      return true;
    } catch (err) {
      console.error('Error clearing watch history:', err);
      return false;
    }
  }, []);

  return {
    history,
    loading,
    error,
    addToHistory,
    clearHistory,
  };
};

/**
 * Custom hook for managing app settings
 * 
 * @returns {Object} - App settings data and functions
 */
export const useAppSettings = () => {
  const [settings, setSettings] = useState({
    autoplay: true,
    darkMode: false,
    downloadQuality: 'medium',
    pushNotifications: true,
  });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Load settings on mount
  useEffect(() => {
    const loadSettings = async () => {
      try {
        setLoading(true);
        const jsonValue = await AsyncStorage.getItem(STORAGE_KEYS.APP_SETTINGS);
        if (jsonValue != null) {
          setSettings(JSON.parse(jsonValue));
        }
      } catch (err) {
        console.error('Error loading settings:', err);
        setError('Failed to load app settings');
      } finally {
        setLoading(false);
      }
    };

    loadSettings();
  }, []);

  // Update settings
  const updateSettings = useCallback(async (newSettings) => {
    try {
      const updatedSettings = { ...settings, ...newSettings };
      setSettings(updatedSettings);
      
      // Save to storage
      const jsonValue = JSON.stringify(updatedSettings);
      await AsyncStorage.setItem(STORAGE_KEYS.APP_SETTINGS, jsonValue);
      
      return true;
    } catch (err) {
      console.error('Error updating settings:', err);
      return false;
    }
  }, [settings]);

  // Reset settings to defaults
  const resetSettings = useCallback(async () => {
    const defaultSettings = {
      autoplay: true,
      darkMode: false,
      downloadQuality: 'medium',
      pushNotifications: true,
    };
    
    try {
      setSettings(defaultSettings);
      
      // Save to storage
      const jsonValue = JSON.stringify(defaultSettings);
      await AsyncStorage.setItem(STORAGE_KEYS.APP_SETTINGS, jsonValue);
      
      return true;
    } catch (err) {
      console.error('Error resetting settings:', err);
      return false;
    }
  }, []);

  return {
    settings,
    loading,
    error,
    updateSettings,
    resetSettings,
  };
};