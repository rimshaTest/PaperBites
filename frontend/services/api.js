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
const TUNNEL_URL = 'https://outlets-faculty-significantly-personal.trycloudflare.com';

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
 * Fetch latest research papers, optionally filtered by category
 * @param {Object} options - Filter options
 * @param {number} options.limit - Maximum number of papers to fetch
 * @param {number} options.offset - Offset for pagination
 * @param {string} options.category - Category to filter by
 * @returns {Promise<Array>} - Promise that resolves to an array of papers
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
 * Ask a question about a specific paper via the Gemini-backed chat agent.
 * @param {string} paperId - ID of the paper to chat about
 * @param {string} question - The question to ask
 * @param {Array<{role: 'user'|'assistant', content: string}>} history - Prior turns in this
 *   conversation - there's no server-side chat memory, so the full history must be resent.
 * @returns {Promise<string>} - Promise that resolves to the assistant's answer text
 */
export const chatAboutPaper = async (paperId, question, history = []) => {
  try {
    const response = await fetch(`${API_BASE_URL}/papers/${paperId}/chat`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ question, history }),
    });

    if (!response.ok) {
      throw new Error(`API error: ${response.status}`);
    }

    const data = await response.json();
    return data.answer;
  } catch (error) {
    console.error(`Error chatting about paper ${paperId}:`, error);
    throw error;
  }
};

/**
 * Resolve a citation string or paper link/DOI into a full paper record, fetching and enriching
 * it (Gemini summary, etc.) server-side if it isn't already in the database. Used by the Saved
 * tab's "add by citation or link" flow.
 * @param {string} query - A citation string, a DOI, or a paper URL
 * @returns {Promise<Object>} - Promise that resolves to the resolved paper (same shape as fetchPaperById)
 * @throws {Error} with message 'not_found' if no paper could be matched
 */
export const resolvePaper = async (query) => {
  const response = await fetch(`${API_BASE_URL}/papers/resolve`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ query }),
  });

  if (response.status === 404) {
    throw new Error('not_found');
  }
  if (!response.ok) {
    throw new Error(`API error: ${response.status}`);
  }

  return response.json();
};

/**
 * Fetch an author's profile (name + their papers)
 * @param {string} authorId - Composite author ID, e.g. "openalex:A123..."
 * @returns {Promise<Object>} - Promise that resolves to {id, name, papers}
 */
export const fetchAuthor = async (authorId) => {
  try {
    const response = await fetch(`${API_BASE_URL}/authors/${encodeURIComponent(authorId)}`);

    if (!response.ok) {
      throw new Error(`API error: ${response.status}`);
    }

    return response.json();
  } catch (error) {
    console.error(`Error fetching author ${authorId}:`, error);
    throw error;
  }
};

/**
 * Fetch all papers published in a given journal/conference
 * @param {string} journalName - Exact journal/conference name
 * @returns {Promise<Object>} - Promise that resolves to {name, papers}
 */
export const fetchJournal = async (journalName) => {
  try {
    const response = await fetch(`${API_BASE_URL}/journals/${encodeURIComponent(journalName)}`);

    if (!response.ok) {
      throw new Error(`API error: ${response.status}`);
    }

    return response.json();
  } catch (error) {
    console.error(`Error fetching journal ${journalName}:`, error);
    throw error;
  }
};