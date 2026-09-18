import { Platform } from 'react-native';
import Constants from 'expo-constants';

// Use your actual IP address that's accessible from your physical device
const COMPUTER_IP = '192.168.0.14'; // Replace with your actual IP

const getApiBaseUrl = () => {
  // Production: use environment variable
  if (process.env.REACT_APP_API_URL) {
    return `${process.env.REACT_APP_API_URL}/api`;
  }
  
  // Development: use localhost or IP
  return Platform.OS === 'web' 
    ? 'http://localhost:8000/api' 
    : `http://${COMPUTER_IP}:8000/api`;
};

const API_BASE_URL = getApiBaseUrl();

console.log(`Using API base URL: ${API_BASE_URL}`);

/**
 * Fetch all videos with optional filtering
 * @param {Object} options - Filter options
 * @param {number} options.limit - Maximum number of videos to fetch
 * @param {number} options.offset - Offset for pagination
 * @param {string} options.keyword - Keyword to filter by
 * @param {boolean} options.publicOnly - Whether to fetch only public videos
 * @returns {Promise<Array>} - Promise that resolves to an array of videos
 */
export const fetchVideos = async (options = {}) => {
  const { limit = 50, offset = 0, keyword, publicOnly = true } = options;
  
  // Build query string
  let queryParams = `?limit=${limit}&offset=${offset}&public_only=${publicOnly}`;
  if (keyword) {
    queryParams += `&keyword=${encodeURIComponent(keyword)}`;
  }
  
  try {
    const response = await fetch(`${API_BASE_URL}/videos${queryParams}`);
    
    if (!response.ok) {
      throw new Error(`API error: ${response.status}`);
    }
    
    return response.json();
  } catch (error) {
    console.error('Error fetching videos:', error);
    throw error;
  }
};

/**
 * Fetch a single video by ID
 * @param {string} videoId - ID of the video to fetch
 * @returns {Promise<Object>} - Promise that resolves to video metadata
 */
export const fetchVideoById = async (videoId) => {
  try {
    const response = await fetch(`${API_BASE_URL}/videos/${videoId}`);
    
    if (!response.ok) {
      throw new Error(`API error: ${response.status}`);
    }
    
    return response.json();
  } catch (error) {
    console.error(`Error fetching video ${videoId}:`, error);
    throw error;
  }
};

/**
 * Fetch all available topics/keywords
 * @returns {Promise<Array>} - Promise that resolves to an array of topics
 */
export const fetchTopics = async () => {
  try {
    const response = await fetch(`${API_BASE_URL}/topics`);

    if (!response.ok) {
      throw new Error(`API error: ${response.status}`);
    }

    return response.json();
  } catch (error) {
    console.error('Error fetching topics:', error);
    throw error;
  }
};

/**
 * Fetch full video metadata for everything a device has bookmarked
 * @param {string} deviceId - Opaque per-device id
 * @returns {Promise<Array>} - Promise that resolves to an array of bookmarked videos, newest first
 */
export const fetchBookmarks = async (deviceId) => {
  try {
    const response = await fetch(`${API_BASE_URL}/bookmarks?device_id=${encodeURIComponent(deviceId)}`);

    if (!response.ok) {
      throw new Error(`API error: ${response.status}`);
    }

    return response.json();
  } catch (error) {
    console.error('Error fetching bookmarks:', error);
    throw error;
  }
};

/**
 * Bookmark a video for a device
 * @param {string} deviceId - Opaque per-device id
 * @param {string} videoId - ID of the video to bookmark
 * @returns {Promise<Object>}
 */
export const addBookmark = async (deviceId, videoId) => {
  const response = await fetch(`${API_BASE_URL}/bookmarks`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ device_id: deviceId, video_id: videoId }),
  });

  if (!response.ok) {
    throw new Error(`API error: ${response.status}`);
  }

  return response.json();
};

/**
 * Remove a device's bookmark on a video
 * @param {string} deviceId - Opaque per-device id
 * @param {string} videoId - ID of the video to un-bookmark
 * @returns {Promise<Object>}
 */
export const removeBookmark = async (deviceId, videoId) => {
  const response = await fetch(
    `${API_BASE_URL}/bookmarks/${encodeURIComponent(videoId)}?device_id=${encodeURIComponent(deviceId)}`,
    { method: 'DELETE' }
  );

  if (!response.ok) {
    throw new Error(`API error: ${response.status}`);
  }

  return response.json();
};