import AsyncStorage from '@react-native-async-storage/async-storage';

// Storage keys
const KEYS = {
  RECENT_SEARCHES: 'paperbites_recent_searches',
  WATCH_HISTORY: 'paperbites_watch_history',
  APP_SETTINGS: 'paperbites_app_settings',
  AUTH_TOKEN: 'paperbites_auth_token',
  AUTH_USER: 'paperbites_auth_user',
};

/**
 * Persist the current session (token + user) after signup/login.
 */
export const saveAuthSession = async (token, user) => {
  try {
    await AsyncStorage.setItem(KEYS.AUTH_TOKEN, token);
    await AsyncStorage.setItem(KEYS.AUTH_USER, JSON.stringify(user));
  } catch (error) {
    console.error('Error saving auth session:', error);
  }
};

/**
 * Read the persisted session, if any.
 * @returns {Promise<{token: string|null, user: Object|null}>}
 */
export const getAuthSession = async () => {
  try {
    const token = await AsyncStorage.getItem(KEYS.AUTH_TOKEN);
    const userJson = await AsyncStorage.getItem(KEYS.AUTH_USER);
    return {
      token: token || null,
      user: userJson ? JSON.parse(userJson) : null,
    };
  } catch (error) {
    console.error('Error loading auth session:', error);
    return { token: null, user: null };
  }
};

/**
 * Clear the persisted session (logout, or an invalid/expired token).
 */
export const clearAuthSession = async () => {
  try {
    await AsyncStorage.multiRemove([KEYS.AUTH_TOKEN, KEYS.AUTH_USER]);
  } catch (error) {
    console.error('Error clearing auth session:', error);
  }
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