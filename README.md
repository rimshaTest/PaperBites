# PaperBites App

A mobile application that displays research paper summaries in a TikTok-style interface. This app is designed to make academic research more accessible and engaging through short video summaries.

## Features

- Vertical swipeable interface similar to TikTok/Reels
- Auto-playing videos with summaries of research papers
- Direct links to original research papers via DOI
- Topic filtering by research interests
- Video favoriting and sharing capabilities
- Offline viewing support

## Project Structure

The project consists of two main parts:

1. **Backend** - Python-based system that:
   - Searches for and downloads research papers
   - Extracts text and summarizes content
   - Generates TikTok-style videos with narration

2. **Frontend** - React Native mobile app that:
   - Displays the videos in a swipeable interface
   - Allows users to interact with the content
   - Provides settings for customizing the experience

## Prerequisites

- Node.js (v14 or higher)
- npm or Yarn
- Expo CLI
- iOS or Android device/simulator

## Installation

### Setting up the frontend

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/paperbites.git
   cd paperbites/frontend
   ```

2. Install dependencies:
   ```bash
   npm install
   # or with Yarn
   yarn install
   ```

3. Start the development server:
   ```bash
   npm start
   # or with Yarn
   yarn start
   ```

4. Follow the Expo instructions to open the app on your device or simulator.

### Connecting to the backend

The app is designed to connect to your PaperBites backend API. Edit the `API_URL` in `api/videoService.js` to point to your backend server.

For development purposes, the app includes mock data so you can test the interface without a backend connection.

## Usage

### Home Screen

The home screen displays a vertical feed of research paper videos. Swipe up and down to navigate between videos. Each video includes:

- Research paper title
- Brief summary
- Key insights
- Relevant keywords as hashtags
- Link to the original paper

### Controls

- Tap the center of the video to play/pause
- Like button to save your favorite videos
- Share button to share the video or paper
- Bookmark button to save for offline viewing

### Settings

The settings screen allows you to customize your experience:

- Toggle autoplay
- Enable/disable dark mode
- Set research interests to customize your feed
- Manage storage and clear cache

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- This app was built using Expo and React Native
- Research papers are accessed through open-access APIs