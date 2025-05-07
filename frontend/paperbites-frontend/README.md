# PaperBites Frontend Implementation Guide

## Overview

This guide provides detailed instructions for integrating the PaperBites frontend with your existing backend. The frontend is built using React Native and Expo, with a file-based routing system for easy navigation.

## File Structure

The frontend code follows this structure:

```
paperbites-frontend/
├── app/                    # Main app screens (Expo Router)
│   ├── index.js            # Home screen
│   ├── video/[id].js       # Video detail screen
│   ├── topics.js           # Topics/categories screen
│   ├── search.js           # Search screen
│   └── _layout.js          # Layout for navigation
├── components/             # Reusable UI components
│   ├── VideoCard.js        # Video card component
│   ├── VideoPlayer.js      # Video player component 
│   ├── TopicChip.js        # Topic/keyword chip component
│   ├── LoadingIndicator.js # Loading state component
│   └── ErrorMessage.js     # Error state component
├── constants/              # App constants
│   ├── Colors.js           # Color scheme
│   └── ApiConfig.js        # API configuration
├── hooks/                  # Custom React hooks
│   ├── useApi.js           # API interaction hooks
│   └── useStorage.js       # Local storage hooks
├── services/               # Service modules
│   ├── api.js              # API service
│   └── storage.js          # Local storage service
└── utils/                  # Utility functions
    └── formatters.js       # Text/date formatters
```

## Integration Steps

Follow these steps to integrate the frontend with your backend:

### 1. Configure API Endpoints

Update the `constants/ApiConfig.js` file to point to your backend API server:

```javascript
// For local development
const BASE_URL = Platform.OS === 'ios' 
  ? 'http://localhost:8000/api' 
  : 'http://10.0.2.2:8000/api';

// For production (replace with your actual backend API URL)
// const BASE_URL = 'https://your-backend-server.com/api';
```

### 2. Install Required Dependencies

Make sure all required dependencies are installed:

```bash
npm install @react-navigation/native @react-navigation/bottom-tabs @react-navigation/native-stack
npm install @react-native-async-storage/async-storage expo-av
npm install expo-status-bar react-native-safe-area-context
npm install react-native-screens
```

### 3. Update API Service

If your backend API has different endpoints or parameters, update the `services/api.js` file to match your API structure.

### 4. Testing with Mock Data

If your backend is not yet ready, you can use mock data for testing:

1. Create a `constants/MockData.js` file with sample videos and topics
2. Update the `services/api.js` file to use mock data when in development mode

### 5. Customizing the UI

To match your branding:

1. Update colors in `constants/Colors.js`
2. Customize component styles as needed
3. Add your logo and other brand assets to the `assets/` folder

## Important Components

### VideoPlayer

The `VideoPlayer` component is responsible for playing videos from S3. It supports:

- Autoplay
- Custom controls
- Error handling
- Loading states

You can customize video playback behavior in `components/VideoPlayer.js`.

### Video Card

The `VideoCard` component displays video previews in the feed. Customize the appearance and information shown in `components/VideoCard.js`.

## Backend API Requirements

The frontend expects these API endpoints:

1. `/api/videos` - Get a list of videos with optional filtering
   - Parameters: limit, offset, keyword, public_only
   - Returns: Array of video objects

2. `/api/videos/{id}` - Get a single video by ID
   - Parameters: id (in path)
   - Returns: Single video object with detailed information

3. `/api/topics` - Get a list of all topics/keywords
   - Returns: Array of topic strings

Each video object should include:
- id: Unique identifier
- title: Video title
- summary: Brief summary of the paper
- videoUrl: URL to the video file in S3
- thumbnailUrl: URL to the video thumbnail (optional)
- doi: DOI of the paper (optional)
- keywords: Array of keywords/topics
- key_insights: Array of key insights
- hashtags: String of hashtags (optional)

## Local Storage

The app uses AsyncStorage to maintain:
- Recent searches
- Favorite videos
- Watch history
- App settings

These are managed through the hooks in `hooks/useStorage.js`.

## Testing the Integration

1. Start your backend server
2. Run the Expo app: `npx expo start`
3. Test the connection by navigating to the Home screen
4. Check that videos load correctly
5. Test search and topic filtering

## Production Deployment

For production deployment:

1. Update `ApiConfig.js` to use your production API URL
2. Build the app for production:
   ```bash
   npx expo build:android
   npx expo build:ios
   ```
3. Publish to app stores following Expo's guidelines

## Troubleshooting

Common issues and solutions:

1. **API connection errors**:
   - Check that the backend server is running
   - Verify network permissions in app.json
   - Ensure API endpoints match

2. **Video playback issues**:
   - Check that S3 URLs are accessible
   - Verify CORS settings on S3 bucket
   - Test with different video formats

3. **Slow performance**:
   - Implement pagination for video lists
   - Optimize video file sizes
   - Cache API responses

For any other issues, refer to the Expo documentation or open an issue in the project repository.