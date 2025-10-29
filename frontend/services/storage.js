import AsyncStorage from '@react-native-async-storage/async-storage';

// Storage keys
const KEYS = {
  RECENT_SEARCHES: 'paperbites_recent_searches',
  FAVORITE_VIDEOS: 'paperbites_favorite_videos',
  WATCH_HISTORY: 'paperbites_watch_history',
  APP_SETTINGS: 'paperbites_app_settings',
};

/**
 * Save recent searches to storage
 * 
 * @param {Array} searches - Array of search strings
 * @returns {Promise<void>}
 */
export const saveRecentSearches = async (searches) => {
  try {
    const jsonValue = JSON.stringify(searches);
    await AsyncStorage.setItem(KEYS.RECENT_SEARCHES, jsonValue);
  } catch (error) {
    console.error('Error saving recent searches:', error);
  }
};

/**
 * Get recent searches from storage
 * 
 * @returns {Promise<Array>} Array of search strings
 */
export const getRecentSearches = async () => {
  try {
    const jsonValue = await AsyncStorage.getItem(KEYS.RECENT_SEARCHES);
    return jsonValue != null ? JSON.parse(jsonValue) : [];
  } catch (error) {
    console.error('Error loading recent searches:', error);
    return [];
  }
};

/**
 * Add a video to favorites
 * 
 * @param {Object} video - Video object
 * @returns {Promise<void>}
 */
export const addFavoriteVideo = async (video) => {
  try {
    // Get current favorites
    const currentFavorites = await getFavoriteVideos();
    
    // Check if already favorited
    if (!currentFavorites.some(fav => fav.id === video.id)) {
      // Add to favorites
      const updatedFavorites = [video, ...currentFavorites];
      const jsonValue = JSON.stringify(updatedFavorites);
      await AsyncStorage.setItem(KEYS.FAVORITE_VIDEOS, jsonValue);
    }
  } catch (error) {
    console.error('Error adding favorite video:', error);
  }
};

/**
 * Remove a video from favorites
 * 
 * @param {string} videoId - ID of video to remove
 * @returns {Promise<void>}
 */
export const removeFavoriteVideo = async (videoId) => {
  try {
    // Get current favorites
    const currentFavorites = await getFavoriteVideos();
    
    // Filter out the video to remove
    const updatedFavorites = currentFavorites.filter(video => video.id !== videoId);
    const jsonValue = JSON.stringify(updatedFavorites);
    await AsyncStorage.setItem(KEYS.FAVORITE_VIDEOS, jsonValue);
  } catch (error) {
    console.error('Error removing favorite video:', error);
  }
};

/**
 * Get all favorite videos
 * 
 * @returns {Promise<Array>} Array of video objects
 */
export const getFavoriteVideos = async () => {
  try {
    const jsonValue = await AsyncStorage.getItem(KEYS.FAVORITE_VIDEOS);
    return jsonValue != null ? JSON.parse(jsonValue) : [];
  } catch (error) {
    console.error('Error loading favorite videos:', error);
    return [];
  }
};

/**
 * Check if a video is in favorites
 * 
 * @param {string} videoId - ID of video to check
 * @returns {Promise<boolean>} True if video is favorited
 */
export const isVideoFavorited = async (videoId) => {
  try {
    const favorites = await getFavoriteVideos();
    return favorites.some(video => video.id === videoId);
  } catch (error) {
    console.error('Error checking if video is favorited:', error);
    return false;
  }
};

/**
 * Add a video to watch history
 * 
 * @param {Object} video - Video object
 * @returns {Promise<void>}
 */
export const addToWatchHistory = async (video) => {
  try {
    // Get current history
    const history = await getWatchHistory();
    
    // Remove if already in history to avoid duplicates
    const filteredHistory = history.filter(item => item.id !== video.id);
    
    // Add to beginning of history with timestamp
    const updatedHistory = [
      { ...video, watchedAt: Date.now() },
      ...filteredHistory
    ];
    
    // Limit history to 50 items
    const limitedHistory = updatedHistory.slice(0, 50);
    
    const jsonValue = JSON.stringify(limitedHistory);
    await AsyncStorage.setItem(KEYS.WATCH_HISTORY, jsonValue);
  } catch (error) {
    console.error('Error adding to watch history:', error);
  }
};

/**
 * Get watch history
 * 
 * @returns {Promise<Array>} Array of video objects with watchedAt timestamps
 */
export const getWatchHistory = async () => {
  try {
    const jsonValue = await AsyncStorage.getItem(KEYS.WATCH_HISTORY);
    return jsonValue != null ? JSON.parse(jsonValue) : [];
  } catch (error) {
    console.error('Error loading watch history:', error);
    return [];
  }
};

/**
 * Clear watch history
 * 
 * @returns {Promise<void>}
 */
export const clearWatchHistory = async () => {
  try {
    await AsyncStorage.setItem(KEYS.WATCH_HISTORY, JSON.stringify([]));
  } catch (error) {
    console.error('Error clearing watch history:', error);
  }
};

/**
 * Save app settings
 * 
 * @param {Object} settings - Settings object
 * @returns {Promise<void>}
 */
export const saveAppSettings = async (settings) => {
  try {
    const jsonValue = JSON.stringify(settings);
    await AsyncStorage.setItem(KEYS.APP_SETTINGS, jsonValue);
  } catch (error) {
    console.error('Error saving app settings:', error);
  }
};

/**
 * Get app settings
 * 
 * @returns {Promise<Object>} Settings object
 */
export const getAppSettings = async () => {
  try {
    const jsonValue = await AsyncStorage.getItem(KEYS.APP_SETTINGS);
    return jsonValue != null ? JSON.parse(jsonValue) : getDefaultSettings();
  } catch (error) {
    console.error('Error loading app settings:', error);
    return getDefaultSettings();
  }
};

/**
 * Get default app settings
 * 
 * @returns {Object} Default settings
 */
const getDefaultSettings = () => {
  return {
    autoplay: true,
    darkMode: false,
    downloadQuality: 'medium',
    pushNotifications: true,
  };
};