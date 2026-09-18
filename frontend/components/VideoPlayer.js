import React from 'react';
import { View, Text, StyleSheet, ActivityIndicator, TouchableOpacity, Dimensions } from 'react-native';
import { useVideoPlayer, VideoView } from 'expo-video';
import { useEvent } from 'expo';
import { Ionicons } from '@expo/vector-icons';

const { width } = Dimensions.get('window');

const VideoPlayer = ({ videoUrl, title, autoplay = false }) => {
  const player = useVideoPlayer(videoUrl, (player) => {
    player.loop = false;
    if (autoplay) {
      player.play();
    }
  });

  const { isPlaying } = useEvent(player, 'playingChange', { isPlaying: player.playing });
  const { status, error: statusError } = useEvent(player, 'statusChange', { status: player.status });
  const { currentTime } = useEvent(player, 'timeUpdate', { currentTime: player.currentTime });

  const isLoading = status === 'loading';
  const playerError = statusError ? `Failed to load video: ${statusError.message}` : null;

  const togglePlayPause = () => {
    if (isPlaying) {
      player.pause();
    } else {
      player.play();
    }
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
        <VideoView
          player={player}
          style={styles.video}
          contentFit="contain"
          nativeControls={false}
        />

        {/* Loading indicator */}
        {isLoading && (
          <View style={styles.overlayContainer}>
            <ActivityIndicator size="large" color="#fff" />
          </View>
        )}

        {/* Error message */}
        {playerError && (
          <View style={styles.overlayContainer}>
            <Text style={styles.errorText}>{playerError}</Text>
          </View>
        )}

        {/* Play/Pause button */}
        {!isLoading && !playerError && (
          <View style={[
            styles.overlayContainer,
            { backgroundColor: isPlaying ? 'transparent' : 'rgba(0, 0, 0, 0.3)' }
          ]}>
            {!isPlaying && (
              <Ionicons name="play" size={60} color="#fff" />
            )}
          </View>
        )}
      </TouchableOpacity>

      {/* Video controls */}
      <View style={styles.controlsContainer}>
        <TouchableOpacity onPress={togglePlayPause} style={styles.controlButton}>
          <Ionicons
            name={isPlaying ? "pause" : "play"}
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
                width: `${player.duration ? (currentTime / player.duration) * 100 : 0}%`
              }
            ]}
          />
        </View>

        {/* Duration */}
        <Text style={styles.durationText}>
          {formatDuration(currentTime)}/{formatDuration(player.duration || 0)}
        </Text>
      </View>
    </View>
  );
};

// Helper function to format duration (expo-video reports time in seconds)
const formatDuration = (seconds) => {
  const totalSeconds = Math.floor(seconds);
  const minutes = Math.floor(totalSeconds / 60);
  const remainingSeconds = totalSeconds % 60;
  return `${minutes}:${remainingSeconds < 10 ? '0' : ''}${remainingSeconds}`;
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
