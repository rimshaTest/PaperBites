import AsyncStorage from '@react-native-async-storage/async-storage';

// Storage keys
const KEYS = {
  AUTH_TOKEN: 'paperbites_auth_token',
  AUTH_USER: 'paperbites_auth_user',
  INTERESTS: 'paperbites_interests',
  SAVED_PAPERS: 'paperbites_saved_papers',
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
 * Get the user's saved topic/category interests.
 * @returns {Promise<Array<string>>}
 */
export const getInterests = async () => {
  try {
    const jsonValue = await AsyncStorage.getItem(KEYS.INTERESTS);
    return jsonValue != null ? JSON.parse(jsonValue) : [];
  } catch (error) {
    console.error('Error loading interests:', error);
    return [];
  }
};

/**
 * Save the user's selected topic/category interests.
 * @param {Array<string>} interests
 */
export const saveInterests = async (interests) => {
  try {
    await AsyncStorage.setItem(KEYS.INTERESTS, JSON.stringify(interests));
  } catch (error) {
    console.error('Error saving interests:', error);
  }
};

/**
 * Whether a paper id is in the device-local saved list.
 * @param {string} paperId
 * @returns {Promise<boolean>}
 */
export const isPaperSaved = async (paperId) => {
  try {
    const jsonValue = await AsyncStorage.getItem(KEYS.SAVED_PAPERS);
    const savedIds = jsonValue != null ? JSON.parse(jsonValue) : [];
    return savedIds.includes(paperId);
  } catch (error) {
    console.error('Error checking saved paper:', error);
    return false;
  }
};

/**
 * Add a paper id to the device-local saved list.
 * @param {string} paperId
 */
export const savePaperId = async (paperId) => {
  try {
    const jsonValue = await AsyncStorage.getItem(KEYS.SAVED_PAPERS);
    const savedIds = jsonValue != null ? JSON.parse(jsonValue) : [];
    if (!savedIds.includes(paperId)) {
      await AsyncStorage.setItem(KEYS.SAVED_PAPERS, JSON.stringify([...savedIds, paperId]));
    }
  } catch (error) {
    console.error('Error saving paper id:', error);
  }
};

/**
 * Remove a paper id from the device-local saved list.
 * @param {string} paperId
 */
export const unsavePaperId = async (paperId) => {
  try {
    const jsonValue = await AsyncStorage.getItem(KEYS.SAVED_PAPERS);
    const savedIds = jsonValue != null ? JSON.parse(jsonValue) : [];
    await AsyncStorage.setItem(
      KEYS.SAVED_PAPERS,
      JSON.stringify(savedIds.filter((id) => id !== paperId))
    );
  } catch (error) {
    console.error('Error unsaving paper id:', error);
  }
};
