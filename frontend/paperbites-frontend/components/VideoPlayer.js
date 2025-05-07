import React, { useState, useRef, useEffect } from 'react';
import { View, Text, StyleSheet, ActivityIndicator, TouchableOpacity, Dimensions } from 'react-native';
import { Video } from 'expo-video';
import { Ionicons } from '@expo/vector-icons';
import Colors from '../constants/Colors';

const { width, height } = Dimensions.get('window');

const VideoPlayer = ({ videoUrl, title, autoplay = false }) => {
  const videoRef = useRef(null);
  const [status, setStatus] = useState({});
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);

  // Handle video loading and playback
  useEffect(() => {
    // Reset states when video URL changes
    setIsLoading(true);
    setError(null);
    
    // Handle autoplay if needed
    if (autoplay && videoRef.current) {
      videoRef.current.playAsync();
    }
    
    return () => {
      // Cleanup: unload video when component unmounts
      if (videoRef.current) {
        videoRef.current.unloadAsync();
      }
    };
  }, [videoUrl, autoplay]);

  // Handle playback status updates
  const handlePlaybackStatusUpdate = (playbackStatus) => {
    if (playbackStatus.isLoaded) {
      setIsLoading(false);
      setStatus(playbackStatus);
    } else if (playbackStatus.error) {
      setIsLoading(false);
      setError(`Error loading video: ${playbackStatus.error}`);
    }
  };

  // Toggle play/pause
  const togglePlayPause = async () => {
    if (videoRef.current) {
      if (status.isPlaying) {
        await videoRef.current.pauseAsync();
      } else {
        await videoRef.current.playAsync();
      }
    }
  };

  // Handle video loading error
  const handleVideoError = (error) => {
    setIsLoading(false);
    setError(`Failed to load video: ${error}`);
  };

  return (
    <View style={styles.container}>
      {/* Video title */}
      {title && <Text style={styles.title}>{title}</Text>}
      
      {/* Video player */}
      <TouchableOpacity 
        style={styles.videoContainer} 
        activeOpacity={0.9} 
        onPress={togglePlayPause}
      >
        <Video
          ref={videoRef}
          source={{ uri: videoUrl }}
          rate={1.0}
          volume={1.0}
          isMuted={false}
          resizeMode="contain"
          shouldPlay={autoplay}
          onPlaybackStatusUpdate={handlePlaybackStatusUpdate}
          onError={handleVideoError}
          style={styles.video}
        />
        
        {/* Loading indicator */}
        {isLoading && (
          <View style={styles.overlayContainer}>
            <ActivityIndicator size="large" color="#fff" />
          </View>
        )}
        
        {/* Error message */}
        {error && (
          <View style={styles.overlayContainer}>
            <Text style={styles.errorText}>{error}</Text>
          </View>
        )}
        
        {/* Play/Pause button */}
        {!isLoading && !error && (
          <View style={[
            styles.overlayContainer, 
            { backgroundColor: status.isPlaying ? 'transparent' : 'rgba(0, 0, 0, 0.3)' }
          ]}>
            {!status.isPlaying && (
              <Ionicons name="play" size={60} color="#fff" />
            )}
          </View>
        )}
      </TouchableOpacity>
      
      {/* Video controls */}
      <View style={styles.controlsContainer}>
        <TouchableOpacity onPress={togglePlayPause} style={styles.controlButton}>
          <Ionicons 
            name={status.isPlaying ? "pause" : "play"} 
            size={24} 
            color="#333" 
          />
        </TouchableOpacity>
        
        {/* Progress indicator */}
        <View style={styles.progressContainer}>
          <View 
            style={[
              styles.progressBar, 
              { 
                width: `${status.positionMillis && status.durationMillis 
                  ? (status.positionMillis / status.durationMillis) * 100 
                  : 0}%` 
              }
            ]} 
          />
        </View>
        
        {/* Duration */}
        <Text style={styles.durationText}>
          {formatDuration(status.positionMillis || 0)}/{formatDuration(status.durationMillis || 0)}
        </Text>
      </View>
    </View>
  );
};

// Helper function to format duration
const formatDuration = (milliseconds) => {
  const totalSeconds = Math.floor(milliseconds / 1000);
  const minutes = Math.floor(totalSeconds / 60);
  const seconds = totalSeconds % 60;
  return `${minutes}:${seconds < 10 ? '0' : ''}${seconds}`;
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    alignItems: 'center',
    backgroundColor: '#f9f9f9',
  },
  title: {
    fontSize: 16,
    fontWeight: 'bold',
    marginVertical: 10,
    paddingHorizontal: 15,
    textAlign: 'center',
  },
  videoContainer: {
    width: width,
    height: width * (9 / 16), // 16:9 aspect ratio
    backgroundColor: '#000',
    justifyContent: 'center',
    alignItems: 'center',
  },
  video: {
    width: '100%',
    height: '100%',
  },
  overlayContainer: {
    ...StyleSheet.absoluteFillObject,
    justifyContent: 'center',
    alignItems: 'center',
  },
  errorText: {
    color: '#fff',
    backgroundColor: 'rgba(0, 0, 0, 0.7)',
    padding: 10,
    borderRadius: 5,
    textAlign: 'center',
  },
  controlsContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    width: '100%',
    paddingHorizontal: 15,
    paddingVertical: 10,
  },
  controlButton: {
    padding: 5,
  },
  progressContainer: {
    flex: 1,
    height: 4,
    backgroundColor: '#e0e0e0',
    marginHorizontal: 10,
    borderRadius: 2,
  },
  progressBar: {
    height: '100%',
    backgroundColor: '#4285F4',
    borderRadius: 2,
  },
  durationText: {
    fontSize: 12,
    color: '#666',
  },
});

export default VideoPlayer;