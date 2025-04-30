import AsyncStorage from '@react-native-async-storage/async-storage';

// API endpoint for fetching videos (update with your actual API URL)
const API_URL = 'http://your-server-address.com:8000/api';

/**
 * Fetch videos from the API with optional caching
 * @param {Object} options - Options for fetching videos
 * @param {boolean} options.useCache - Whether to use cached videos
 * @param {boolean} options.forceRefresh - Whether to force refresh from API
 * @param {string} options.keyword - Optional keyword to filter by
 * @returns {Promise<Array>} Array of video objects
 */
export const fetchVideos = async ({ 
  useCache = true, 
  forceRefresh = false,
  keyword = null
} = {}) => {
  const cacheKey = keyword ? `videos_${keyword}` : 'videos';
  
  // Check cache first if enabled and not forcing refresh
  if (useCache && !forceRefresh) {
    try {
      const cachedVideos = await AsyncStorage.getItem(cacheKey);
      if (cachedVideos) {
        return JSON.parse(cachedVideos);
      }
    } catch (error) {
      console.error('Error reading from cache:', error);
    }
  }

  // Build the API URL with any query parameters
  let url = `${API_URL}/videos`;
  const params = new URLSearchParams();
  
  if (keyword) {
    params.append('keyword', keyword);
  }
  
  // Add query parameters if there are any
  if (params.toString()) {
    url += `?${params.toString()}`;
  }

  // Fetch from API
  try {
    const response = await fetch(url);
    if (!response.ok) {
      throw new Error(`API error: ${response.status}`);
    }
    
    const videos = await response.json();
    
    // Cache the fetched data
    if (useCache) {
      try {
        await AsyncStorage.setItem(cacheKey, JSON.stringify(videos));
      } catch (error) {
        console.error('Error saving to cache:', error);
      }
    }
    
    return videos;
  } catch (error) {
    console.error('Error fetching videos:', error);
    throw error;
  }
};

/**
 * Fetch a specific video by ID
 * @param {string} videoId - The ID of the video to fetch
 * @param {boolean} useCache - Whether to use cached data
 * @returns {Promise<Object>} Video object
 */
export const fetchVideoById = async (videoId, useCache = true) => {
  if (useCache) {
    try {
      // First try to find in the videos cache
      const cachedVideos = await AsyncStorage.getItem('videos');
      if (cachedVideos) {
        const videos = JSON.parse(cachedVideos);
        const video = videos.find(v => v.id === videoId);
        if (video) {
          return video;
        }
      }
      
      // Then check if we have this specific video cached
      const cachedVideo = await AsyncStorage.getItem(`video_${videoId}`);
      if (cachedVideo) {
        return JSON.parse(cachedVideo);
      }
    } catch (error) {
      console.error('Error reading from cache:', error);
    }
  }
  
  // Fetch from API
  try {
    const response = await fetch(`${API_URL}/videos/${videoId}`);
    if (!response.ok) {
      throw new Error(`API error: ${response.status}`);
    }
    
    const video = await response.json();
    
    // Cache the video
    try {
      await AsyncStorage.setItem(`video_${videoId}`, JSON.stringify(video));
    } catch (error) {
      console.error('Error saving to cache:', error);
    }
    
    return video;
  } catch (error) {
    console.error(`Error fetching video ID ${videoId}:`, error);
    throw error;
  }
};

/**
 * Fetch popular topics/keywords
 * @param {boolean} useCache - Whether to use cached data
 * @returns {Promise<Array>} Array of topic strings
 */
export const fetchTopics = async (useCache = true) => {
  if (useCache) {
    try {
      const cachedTopics = await AsyncStorage.getItem('topics');
      if (cachedTopics) {
        return JSON.parse(cachedTopics);
      }
    } catch (error) {
      console.error('Error reading topics from cache:', error);
    }
  }
  
  // Fetch from API
  try {
    const response = await fetch(`${API_URL}/topics`);
    if (!response.ok) {
      throw new Error(`API error: ${response.status}`);
    }
    
    const topics = await response.json();
    
    // Cache the topics
    try {
      await AsyncStorage.setItem('topics', JSON.stringify(topics));
    } catch (error) {
      console.error('Error saving topics to cache:', error);
    }
    
    return topics;
  } catch (error) {
    console.error('Error fetching topics:', error);
    throw error;
  }
};

/**
 * Save a video to user's favorites
 * @param {string} videoId - The ID of the video to save
 * @returns {Promise<boolean>} Success status
 */
export const saveVideo = async (videoId) => {
  try {
    // Get current saved videos
    const savedVideosString = await AsyncStorage.getItem('savedVideos');
    const savedVideos = savedVideosString ? JSON.parse(savedVideosString) : [];
    
    // Add the video if not already saved
    if (!savedVideos.includes(videoId)) {
      savedVideos.push(videoId);
      await AsyncStorage.setItem('savedVideos', JSON.stringify(savedVideos));
    }
    
    return true;
  } catch (error) {
    console.error('Error saving video:', error);
    return false;
  }
};

/**
 * Get all saved videos
 * @returns {Promise<Array>} Array of saved video objects
 */
export const getSavedVideos = async () => {
  try {
    const savedVideosString = await AsyncStorage.getItem('savedVideos');
    const savedVideoIds = savedVideosString ? JSON.parse(savedVideosString) : [];
    
    // Fetch full video objects for all saved IDs
    const savedVideos = [];
    for (const videoId of savedVideoIds) {
      try {
        const video = await fetchVideoById(videoId);
        if (video) {
          savedVideos.push(video);
        }
      } catch (error) {
        console.error(`Error fetching saved video ${videoId}:`, error);
      }
    }
    
    return savedVideos;
  } catch (error) {
    console.error('Error getting saved videos:', error);
    return [];
  }
};

/**
 * Clear all cached data
 * @returns {Promise<boolean>} Success status
 */
export const clearCache = async () => {
  try {
    const keys = await AsyncStorage.getAllKeys();
    const videoCacheKeys = keys.filter(key => 
      key === 'videos' || 
      key === 'topics' || 
      key.startsWith('video_') || 
      key.startsWith('videos_')
    );
    
    await AsyncStorage.multiRemove(videoCacheKeys);
    return true;
  } catch (error) {
    console.error('Error clearing cache:', error);
    return false;
  }
};