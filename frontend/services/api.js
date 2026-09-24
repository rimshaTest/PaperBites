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
const TUNNEL_URL = 'https://foster-preservation-oil-unnecessary.trycloudflare.com';

const getApiBaseUrl = () => {
  // Set in a .env file as EXPO_PUBLIC_API_URL=http://<host>:8000 (no trailing /api - that's
  // added below). Only vars prefixed EXPO_PUBLIC_ are inlined into the app bundle by Expo's
  // Metro config; a plain REACT_APP_API_URL (the Create React App convention) is never set at
  // runtime here and silently falls through, which is what was happening before this fix.
  if (process.env.EXPO_PUBLIC_API_URL) {
    return `${process.env.EXPO_PUBLIC_API_URL}/api`;
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
 * Scholar/OpenAlex/Crossref, no video generation involved). This is the primary feed now that
 * video generation is a backburner feature.
 * @param {Object} options - Filter options
 * @param {number} options.limit - Maximum number of papers to fetch
 * @param {number} options.offset - Offset for pagination
 * @param {string} options.category - Category to filter by
 * @param {string} [options.token] - Session token; when present, the feed is hard-filtered to
 *   the signed-in user's chosen interests (see /api/interests), if they've set any
 * @returns {Promise<Array>} - Promise that resolves to an array of papers, newest first
 */
export const fetchPapers = async (options = {}) => {
  const { limit = 50, offset = 0, category, token } = options;

  let queryParams = `?limit=${limit}&offset=${offset}`;
  if (category) {
    queryParams += `&category=${encodeURIComponent(category)}`;
  }

  try {
    const response = await fetch(`${API_BASE_URL}/papers${queryParams}`, {
      headers: token ? { Authorization: `Bearer ${token}` } : undefined,
    });

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
 * Fetch an author's name and every paper of theirs in PaperBites
 * @param {string} authorId - ID of the author (e.g. "semantic_scholar:12345")
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
 * Fetch every paper published in a given journal/venue
 * @param {string} journalName - Name of the journal
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

/**
 * Fetch the signed-in user's chosen topic interests
 * @param {string} token - Session token from login/signup
 * @returns {Promise<Array<string>>}
 */
export const fetchInterests = async (token) => {
  try {
    const response = await fetch(`${API_BASE_URL}/interests`, {
      headers: { Authorization: `Bearer ${token}` },
    });

    if (!response.ok) {
      throw new Error(`API error: ${response.status}`);
    }

    const data = await response.json();
    return data.interests;
  } catch (error) {
    console.error('Error fetching interests:', error);
    throw error;
  }
};

/**
 * Replace the signed-in user's chosen topic interests
 * @param {string} token - Session token from login/signup
 * @param {Array<string>} interests
 * @returns {Promise<Array<string>>}
 */
export const saveInterests = async (token, interests) => {
  const response = await fetch(`${API_BASE_URL}/interests`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify({ interests }),
  });

  if (!response.ok) {
    throw new Error(`API error: ${response.status}`);
  }

  const data = await response.json();
  return data.interests;
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

/**
 * Resolve a raw pasted citation (MLA, APA, or any other style) OR a direct link to the paper's
 * page (e.g. an open-access journal article URL) into candidate matches, for the first step of
 * the add-paper-by-citation flow.
 * @param {string} token - Session token from login/signup
 * @param {string} input - The raw citation text or paper URL as pasted/typed by the user
 * @returns {Promise<Array>} - Promise that resolves to candidate matches: each
 *   {doi, title, authors, journal, published_date, url, is_open_access}
 */
export const searchPaperByCitation = async (token, input) => {
  const response = await fetch(`${API_BASE_URL}/papers/citation/search`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify({ citation: input }),
  });

  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new Error(body.detail || `API error: ${response.status}`);
  }

  const data = await response.json();
  return data.candidates;
};

/**
 * Save a confirmed citation-search candidate as a real paper (server-side it's run through the
 * same enrichment pipeline the discovery feed uses - including a Gemini-chosen category, picked
 * from the paper's abstract/full text in the same call that generates its summary) and bookmark
 * it for the signed-in user.
 * @param {string} token - Session token from login/signup
 * @param {Object} candidate - One of the candidates returned by searchPaperByCitation
 * @returns {Promise<Object>} - Promise that resolves to the saved paper
 */
export const addPaperByCitation = async (token, candidate) => {
  const response = await fetch(`${API_BASE_URL}/papers/citation/confirm`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify(candidate),
  });

  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new Error(body.detail || `API error: ${response.status}`);
  }

  return response.json();
};

/**
 * Queue a citation/URL the automated search couldn't match, for manual admin review - the
 * fallback for when search/add fails outright (see add-paper.js's empty-results state).
 * @param {string} token - Session token from login/signup
 * @param {string} input - The citation text or URL the user originally entered
 * @returns {Promise<Object>} - Promise that resolves to {status, id}
 */
export const submitPaperForReview = async (token, input) => {
  const response = await fetch(`${API_BASE_URL}/papers/citation/review`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify({ input }),
  });

  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new Error(body.detail || `API error: ${response.status}`);
  }

  return response.json();
};

/**
 * Fetch the signed-in user's profile - Tier 1 (cache-safe) and Tier 2 (sensitive-context, with
 * per-field consent flags) fields.
 * @param {string} token - Session token from login/signup
 * @returns {Promise<{tier1: Object, tier2: {fields: Object, consent: Object}}>}
 */
export const fetchProfile = async (token) => {
  const response = await fetch(`${API_BASE_URL}/profile`, {
    headers: { Authorization: `Bearer ${token}` },
  });

  if (!response.ok) {
    throw new Error(`API error: ${response.status}`);
  }

  return response.json();
};

/**
 * Update the signed-in user's Tier 1 (cache-safe) profile fields.
 * @param {string} token - Session token from login/signup
 * @param {Object} fields - field_of_study, education_level, general_interests, location
 * @returns {Promise<Object>} - the updated Tier 1 fields
 */
export const saveProfileTier1 = async (token, fields) => {
  const response = await fetch(`${API_BASE_URL}/profile/tier1`, {
    method: 'PUT',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify({ fields }),
  });

  if (!response.ok) {
    throw new Error(`API error: ${response.status}`);
  }

  const data = await response.json();
  return data.tier1;
};

/**
 * Update the signed-in user's Tier 2 (sensitive-context) profile fields and their per-field
 * consent flags (used_for_personalization, used_for_feed_relevance).
 * @param {string} token - Session token from login/signup
 * @param {Object} fields
 * @param {Object} consent - {[fieldName]: {used_for_personalization, used_for_feed_relevance}}
 * @returns {Promise<{fields: Object, consent: Object}>}
 */
export const saveProfileTier2 = async (token, fields, consent) => {
  const response = await fetch(`${API_BASE_URL}/profile/tier2`, {
    method: 'PUT',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify({ fields, consent }),
  });

  if (!response.ok) {
    throw new Error(`API error: ${response.status}`);
  }

  const data = await response.json();
  return data.tier2;
};