import { Platform } from 'react-native';
import Constants from 'expo-constants';

// Helper function to determine the appropriate API URL
const getApiBaseUrl = () => {
  // Development flag
  const isDev = __DEV__;
  
  // If in production, use the production URL
  if (!isDev) {
    return 'https://your-production-server.com/api';
  }
  
  // For Android physical devices
  if (Platform.OS === 'android' && Constants.isDevice) {
    // Use the IP address of your development machine
    // Your phone doesn't use 'localhost' to reach your computer
    return 'http://192.168.1.26:8000/api';
  }
  
  // For iOS simulator
  if (Platform.OS === 'ios') {
    return 'http://localhost:8000/api';
  }
  
  // Default fallback
  return 'http://localhost:8000/api';
};

// API base URL
const BASE_URL = getApiBaseUrl();

// Helper function to build API URLs
const buildUrl = (endpoint, queryParams = {}) => {
  const url = new URL(`${BASE_URL}${endpoint}`);
  
  // Add query parameters
  Object.keys(queryParams).forEach(key => {
    if (queryParams[key] !== undefined && queryParams[key] !== null) {
      url.searchParams.append(key, queryParams[key]);
    }
  });
  
  return url.toString();
};

// API configuration
const ApiConfig = {
  BASE_URL,
  ENDPOINTS: {
    VIDEOS: '/videos',
    VIDEO_DETAIL: (id) => `/videos/${id}`,
    TOPICS: '/topics',
  },
  TIMEOUT: 10000, // 10 seconds
  PAGE_SIZE: 10,
  buildUrl,
  
  // Default fetch options
  defaultOptions: {
    headers: {
      'Content-Type': 'application/json',
      'Accept': 'application/json',
    },
  },
  
  // Helper function to handle API errors
  handleApiError: (error, fallbackMessage = 'An error occurred') => {
    console.error('API Error:', error);
    
    if (error.response) {
      // Server responded with a non-2xx status
      return `Server error: ${error.response.status}`;
    } else if (error.request) {
      // Request was made but no response received
      return 'Network error: No response from server';
    } else {
      // Something else went wrong
      return fallbackMessage;
    }
  }
};

export default ApiConfig;