import React, { useEffect, useRef } from 'react';
import { View, StyleSheet, Dimensions } from 'react-native';
import { Video } from 'expo-av';
import * as SplashScreen from 'expo-splash-screen';

// Prevent the native splash screen from hiding automatically
SplashScreen.preventAutoHideAsync();

const VideoSplashScreen = ({ onFinish, videoSource }) => {
  const videoRef = useRef(null);
  
  useEffect(() => {
    // Hide the native splash screen
    SplashScreen.hideAsync();
    
    // Play the video
    if (videoRef.current) {
      videoRef.current.playAsync();
    }
  }, []);
  
  // Handle video completion
  const handlePlaybackStatusUpdate = (status) => {
    if (status.didJustFinish) {
      // Video playback is complete
      if (onFinish) {
        onFinish();
      }
    }
  };
  
  return (
    <View style={styles.container}>
      <Video
        ref={videoRef}
        source={videoSource}
        style={styles.video}
        resizeMode="cover"
        shouldPlay={false} // We'll manually play it in useEffect
        isLooping={false}
        onPlaybackStatusUpdate={handlePlaybackStatusUpdate}
      />
    </View>
  );
};

const { width, height } = Dimensions.get('window');

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#000', // Can be customized to match your video background
  },
  video: {
    width: width,
    height: height,
  },
});

export default VideoSplashScreen;