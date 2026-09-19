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
 * Fetch the paper feed - fetched via the backend's `fetch-latest` pipeline (Semantic
 * Scholar/OpenAlex, no video generation involved). This is the primary feed now that video
 * generation is a backburner feature.
 * @param {Object} options - Filter options
 * @param {number} options.limit - Maximum number of papers to fetch
 * @param {number} options.offset - Offset for pagination
 * @param {string} options.category - Category to filter by
 * @returns {Promise<Array>} - Promise that resolves to an array of papers, newest first
 */
export const fetchPapers = async (options = {}) => {
  const { limit = 50, offset = 0, category } = options;

  let queryParams = `?limit=${limit}&offset=${offset}`;
  if (category) {
    queryParams += `&category=${encodeURIComponent(category)}`;
  }

  try {
    const response = await fetch(`${API_BASE_URL}/papers${queryParams}`);

    if (!response.ok) {
      throw new Error(`API error: ${response.status}`);
    }

    return response.json();
  } catch (error) {
    console.error('Error fetching papers:', error);
    throw error;
  }
};

/**
 * Fetch a single paper by ID
 * @param {string} paperId - ID of the paper to fetch
 * @returns {Promise<Object>} - Promise that resolves to paper metadata
 */
export const fetchPaperById = async (paperId) => {
  try {
    const response = await fetch(`${API_BASE_URL}/papers/${paperId}`);

    if (!response.ok) {
      throw new Error(`API error: ${response.status}`);
    }

    return response.json();
  } catch (error) {
    console.error(`Error fetching paper ${paperId}:`, error);
    throw error;
  }
};

/**
 * Fetch the fixed list of paper categories
 * @returns {Promise<Array<string>>} - Promise that resolves to an array of category names
 */
export const fetchCategories = async () => {
  try {
    const response = await fetch(`${API_BASE_URL}/categories`);

    if (!response.ok) {
      throw new Error(`API error: ${response.status}`);
    }

    return response.json();
  } catch (error) {
    console.error('Error fetching categories:', error);
    throw error;
  }
};

/**
 * Fetch full paper metadata for everything the signed-in user has bookmarked
 * @param {string} token - Session token from login/signup
 * @returns {Promise<Array>} - Promise that resolves to an array of bookmarked papers, newest first
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
 * Bookmark a paper for the signed-in user
 * @param {string} token - Session token from login/signup
 * @param {string} paperId - ID of the paper to bookmark
 * @returns {Promise<Object>}
 */
export const addBookmark = async (token, paperId) => {
  const response = await fetch(`${API_BASE_URL}/bookmarks`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify({ video_id: paperId }),
  });

  if (!response.ok) {
    throw new Error(`API error: ${response.status}`);
  }

  return response.json();
};

/**
 * Remove the signed-in user's bookmark on a paper
 * @param {string} token - Session token from login/signup
 * @param {string} paperId - ID of the paper to un-bookmark
 * @returns {Promise<Object>}
 */
export const removeBookmark = async (token, paperId) => {
  const response = await fetch(
    `${API_BASE_URL}/bookmarks/${encodeURIComponent(paperId)}`,
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