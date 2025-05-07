import React, { useState, useEffect } from 'react';
import { View, StyleSheet } from 'react-native';
import { StatusBar } from 'expo-status-bar';
import * as Font from 'expo-font';
import { Ionicons } from '@expo/vector-icons';
import VideoSplashScreen from './components/VideoSplashScreen';
import AppNavigator from './app/_layout';

export default function App() {
  const [isReady, setIsReady] = useState(false);
  const [showSplash, setShowSplash] = useState(true);

  // Load assets and fonts
  useEffect(() => {
    const loadResourcesAsync = async () => {
      try {
        // Load icon fonts and other required assets
        await Font.loadAsync(Ionicons.font);
        
        setIsReady(true);
      } catch (error) {
        console.error('Error loading resources:', error);
        setIsReady(true); // Continue anyway
      }
    };

    loadResourcesAsync();
  }, []);

  // Handle splash screen completion
  const handleSplashFinish = () => {
    setShowSplash(false);
  };

  // Show video splash screen if not ready or still in splash phase
  if (!isReady || showSplash) {
    return (
      <VideoSplashScreen 
        onFinish={handleSplashFinish}
        videoSource={require('./assets/splash-video.mp4')}
      />
    );
  }

  // Show the actual app
  return (
    <>
      <StatusBar style="auto" />
      <AppNavigator />
    </>
  );
}