import { Platform } from 'react-native';
import Constants from 'expo-constants';

// Only used as a fallback on networks that allow direct device-to-device LAN connections
// (many public/shared WiFi networks block this via AP/client isolation, in which case a
// physical device can't reach this IP no matter how correct it is).
const COMPUTER_IP = '10.212.104.176'; // Replace with your actual IP

// Cloudflare quick tunnel to the backend (localhost:8000) - needed on networks with client
// isolation, where the phone can't reach the laptop directly by LAN IP. Quick tunnel URLs are
// ephemeral (a new one is generated each time `cloudflared tunnel --url http://localhost:8000`
// is started), so update this when it changes.
const TUNNEL_URL = 'https://altered-possibility-far-finals.trycloudflare.com';

const getApiBaseUrl = () => {
  // Production: use environment variable
  if (process.env.REACT_APP_API_URL) {
    return `${process.env.REACT_APP_API_URL}/api`;
  }

  if (Platform.OS === 'web') {
    return 'http://localhost:8000/api';
  }

  return TUNNEL_URL ? `${TUNNEL_URL}/api` : `http://${COMPUTER_IP}:8000/api`;
};

export const API_BASE_URL = getApiBaseUrl();

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
 * Fetch full video metadata for everything the signed-in user has bookmarked
 * @param {string} token - Session token from login/signup
 * @returns {Promise<Array>} - Promise that resolves to an array of bookmarked videos, newest first
 */
export const fetchBookmarks = async (token) => {
  try {
    const response = await fetch(`${API_BASE_URL}/bookmarks`, {
      headers: { Authorization: `Bearer ${token}` },
    });

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
 * Bookmark a video for the signed-in user
 * @param {string} token - Session token from login/signup
 * @param {string} videoId - ID of the video to bookmark
 * @returns {Promise<Object>}
 */
export const addBookmark = async (token, videoId) => {
  const response = await fetch(`${API_BASE_URL}/bookmarks`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify({ video_id: videoId }),
  });

  if (!response.ok) {
    throw new Error(`API error: ${response.status}`);
  }

  return response.json();
};

/**
 * Remove the signed-in user's bookmark on a video
 * @param {string} token - Session token from login/signup
 * @param {string} videoId - ID of the video to un-bookmark
 * @returns {Promise<Object>}
 */
export const removeBookmark = async (token, videoId) => {
  const response = await fetch(
    `${API_BASE_URL}/bookmarks/${encodeURIComponent(videoId)}`,
    {
      method: 'DELETE',
      headers: { Authorization: `Bearer ${token}` },
    }
  );

  if (!response.ok) {
    throw new Error(`API error: ${response.status}`);
  }

  return response.json();
};