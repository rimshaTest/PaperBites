import { Platform } from 'react-native';
import Constants from 'expo-constants';

// Helper function to determine the appropriate API URL
const getApiBaseUrl = () => {
  // Check if we're in production
  const isProduction = !__DEV__;
  
  if (isProduction) {
    // Use production API URL
    return 'https://your-production-api.com/api';
  } else {
    // In development, handle platform-specific URLs
    if (Platform.OS === 'ios') {
      // iOS simulator uses localhost
      return 'http://localhost:8000/api';
    } else if (Platform.OS === 'android') {
      // Android emulator uses 10.0.2.2 (Android's special IP for host loopback)
      // But physical Android devices need the actual IP address
      
      // A common approach is to provide a development URL in app.config.js or through environment variables
      const devServerIP = Constants.expoConfig?.extra?.devServerIP || '192.168.0.14'; // Replace with your IP
      
      // For emulator
      if (Constants.isDevice) {
        // Physical device
        return `http://${devServerIP}:8000/api`;
      } else {
        // Emulator
        return 'http://10.0.2.2:8000/api';
      }
    } else {
      // Web or other platforms
      return '/api'; // Relative path for web
    }
  }
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