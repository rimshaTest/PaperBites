// components/SimpleScreen.tsx
import React, { useState } from 'react';
import { View, Text, StyleSheet, ActivityIndicator, Platform } from 'react-native';
import { Video, ResizeMode } from 'expo-av'; // Using expo-av for now

interface SimpleScreenProps {
  message?: string;
  videoUrl?: string;
}

const SimpleScreen: React.FC<SimpleScreenProps> = ({ message, videoUrl }) => {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Add a console note about the deprecation
  React.useEffect(() => {
    console.log("Note: Using expo-av for video which is deprecated. Will update to expo-video when it's fully available.");
  }, []);

  return (
    <View style={styles.screenContainer}>
      <Text style={styles.messageText}>{message || "Hello World!"}</Text>
      
      {videoUrl && (
        <View style={styles.videoContainer}>
          <Video
            source={{ uri: videoUrl }}
            style={styles.video}
            resizeMode={ResizeMode.CONTAIN}
            shouldPlay
            useNativeControls
            onLoad={() => setLoading(false)}
            onError={(error) => {
              console.error('Video playback error:', error);
              setError('Failed to play video');
              setLoading(false);
            }}
          />
          
          {loading && (
            <View style={styles.overlay}>
              <ActivityIndicator size="large" color="#fff" />
              <Text style={styles.loadingText}>Loading video...</Text>
            </View>
          )}
          
          {error && (
            <View style={styles.overlay}>
              <Text style={styles.errorText}>Error: {error}</Text>
            </View>
          )}
        </View>
      )}
    </View>
  );
};

const styles = StyleSheet.create({
  screenContainer: {
    backgroundColor: '#ffffff',
    padding: 20,
    borderRadius: 10,
    // Fix shadow warnings by using appropriate shadows for web and native
    ...Platform.select({
      web: {
        boxShadow: '0px 2px 4px rgba(0, 0, 0, 0.1)',
      },
      default: {
        elevation: 2,
      },
    }),
    marginVertical: 10,
    width: '80%',
    maxWidth: 400,
    alignItems: 'center',
  },
  messageText: {
    fontSize: 18,
    color: '#333',
    textAlign: 'center',
    marginBottom: 15,
  },
  videoContainer: {
    width: '100%',
    height: 200,
    marginTop: 10,
    borderRadius: 8,
    overflow: 'hidden',
    backgroundColor: '#000',
    position: 'relative',
  },
  video: {
    width: '100%',
    height: '100%',
  },
  overlay: {
    position: 'absolute',
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: 'rgba(0,0,0,0.5)',
  },
  loadingText: {
    color: '#fff',
    marginTop: 10,
  },
  errorText: {
    color: '#fff',
    textAlign: 'center',
    padding: 10,
  },
});

export default SimpleScreen;