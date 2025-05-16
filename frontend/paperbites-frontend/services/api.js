// services/api.js
import { Platform } from 'react-native';
import Constants from 'expo-constants';

// Determine the API base URL based on the environment
const getApiBaseUrl = () => {
  // Development flag
  const isDev = __DEV__;
  
  // If in production, use the production URL
  if (!isDev) {
    return 'https://your-production-server.com/api';
  }
  
  // For development, use different URLs depending on the platform
  if (Platform.OS === 'web') {
    return 'http://localhost:8000/api';
  } else if (Platform.OS === 'ios') {
    // iOS simulator uses localhost
    return 'http://localhost:8000/api';
  } else if (Platform.OS === 'android') {
    // Android emulator uses 10.0.2.2 to refer to the host machine
    const isEmulator = !Constants.isDevice;
    if (isEmulator) {
      return 'http://10.0.2.2:8000/api'; // For emulator
    } else {
      // For physical device, use the local network IP of your computer
      return 'http://192.168.1.26:8000/api';
    }
  }
  
  // Default fallback
  return 'http://localhost:8000/api';
};

// API base URL
const API_BASE_URL = getApiBaseUrl();

console.log(`Using API base URL: ${API_BASE_URL}`);
console.log(`Running on: ${Platform.OS}, isDevice: ${Constants.isDevice || false}`);

/**
 * Fetch all videos with optional filtering
 * @param {Object} options - Filter options
 * @param {number} options.limit - Maximum number of videos to fetch
 * @param {number} options.offset - Offset for pagination
 * @param {string} options.keyword - Keyword to filter by
 * @param {boolean} options.publicOnly - Whether to fetch only public videos
 * @returns {Promise<Array>} - Promise that resolves to an array of videos
 */
// In your services/api.js file
export const fetchVideos = async (options = {}) => {
  const { limit = 50, offset = 0, keyword, publicOnly = true } = options;
  
  console.log('📞 API CALL: fetchVideos with options:', JSON.stringify(options));
  
  let queryParams = `?limit=${limit}&offset=${offset}&public_only=${publicOnly}`;
  if (keyword) {
    queryParams += `&keyword=${encodeURIComponent(keyword)}`;
  }
  
  const url = `${API_BASE_URL}/videos${queryParams}`;
  console.log('📞 Fetching URL:', url);
  
  try {
    console.log('📞 Starting fetch request...');
    const response = await fetch(url);
    console.log(`📞 Response received with status: ${response.status}`);
    
    if (!response.ok) {
      console.error(`📞 API error with status ${response.status}`);
      throw new Error(`API error: ${response.status}`);
    }
    
    console.log('📞 Parsing response as JSON...');
    const data = await response.json();
    console.log(`📞 Successfully parsed data with ${data.length} items`);
    return data;
  } catch (error) {
    console.error('📞 FETCH ERROR:', error.name, error.message);
    // Log additional details about the error
    if (error.cause) console.error('📞 Error cause:', error.cause);
    if (error.stack) console.error('📞 Stack trace:', error.stack);
    throw new Error(`Failed to load videos: ${error.message}`);
  }
};

/**
 * Fetch a single video by ID
 * @param {string} videoId - ID of the video to fetch
 * @returns {Promise<Object>} - Promise that resolves to video metadata
 */
export const fetchVideoById = async (videoId) => {
  try {
    console.log(`Fetching video with ID: ${videoId}`);
    
    const response = await fetch(`${API_BASE_URL}/videos/${videoId}`);
    
    if (!response.ok) {
      throw new Error(`API error: ${response.status}`);
    }
    
    return response.json();
  } catch (error) {
    console.error(`Error fetching video ${videoId}:`, error);
    throw error; // Re-throw to let the calling code handle it
  }
};

/**
 * Fetch all available topics/keywords
 * @returns {Promise<Array>} - Promise that resolves to an array of topics
 */
export const fetchTopics = async () => {
  try {
    console.log('Fetching topics from API');
    
    const response = await fetch(`${API_BASE_URL}/topics`);
    
    if (!response.ok) {
      throw new Error(`API error: ${response.status}`);
    }
    
    return response.json();
  } catch (error) {
    console.error('Error fetching topics:', error);
    throw error; // Re-throw to let the calling code handle it
  }
};