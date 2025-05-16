// components/FullscreenVideoPlayer.js
import React, { useState, useRef, useEffect } from 'react';
import { 
  View, 
  Text, 
  StyleSheet, 
  Dimensions, 
  TouchableOpacity,
  Animated,
  TouchableWithoutFeedback
} from 'react-native';
import { Video } from 'expo-video'; // Changed from expo-av
import { Ionicons } from '@expo/vector-icons';
import { BlurView } from 'expo-blur';
import { useFavoriteVideos } from '../hooks/useStorage';
import VideoProgressBar from './VideoProgressBar';

const { width, height } = Dimensions.get('window');

const FullscreenVideoPlayer = ({ video, isActive, onMoreInfo, onShare }) => {
  const videoRef = useRef(null);
  const [status, setStatus] = useState({});
  const [videoLoaded, setVideoLoaded] = useState(false);
  const [isMuted, setIsMuted] = useState(false);
  const [infoVisible, setInfoVisible] = useState(true);
  const { isFavorite, toggleFavorite } = useFavoriteVideos();
  const [isLiked, setIsLiked] = useState(false);
  
  // Animation values
  const fadeAnim = useRef(new Animated.Value(1)).current;
  const infoTimeout = useRef(null);

  // Check if the current video is liked
  useEffect(() => {
    const checkLikeStatus = async () => {
      const favorited = await isFavorite(video.id);
      setIsLiked(favorited);
    };
    
    checkLikeStatus();
  }, [video.id, isFavorite]);

  // Handle video playback when active state changes
  useEffect(() => {
    if (videoRef.current) {
      if (isActive) {
        videoRef.current.play(); // Changed from playAsync()
      } else {
        videoRef.current.pause(); // Changed from pauseAsync()
      }
    }
    
    return () => {
      if (infoTimeout.current) {
        clearTimeout(infoTimeout.current);
      }
    };
  }, [isActive]);

  // Auto-hide info after delay
  const showInfo = () => {
    setInfoVisible(true);
    
    // Animate fade in
    Animated.timing(fadeAnim, {
      toValue: 1,
      duration: 200,
      useNativeDriver: true,
    }).start();
    
    // Clear any existing timeout
    if (infoTimeout.current) {
      clearTimeout(infoTimeout.current);
    }
    
    // Set timeout to hide info
    infoTimeout.current = setTimeout(() => {
      Animated.timing(fadeAnim, {
        toValue: 0,
        duration: 500,
        useNativeDriver: true,
      }).start(() => {
        setInfoVisible(false);
      });
    }, 5000);
  };

  // Toggle info visibility
  const toggleInfo = () => {
    if (infoVisible) {
      Animated.timing(fadeAnim, {
        toValue: 0,
        duration: 200,
        useNativeDriver: true,
      }).start(() => {
        setInfoVisible(false);
      });
      
      if (infoTimeout.current) {
        clearTimeout(infoTimeout.current);
        infoTimeout.current = null;
      }
    } else {
      setInfoVisible(true);
      
      Animated.timing(fadeAnim, {
        toValue: 1,
        duration: 200,
        useNativeDriver: true,
      }).start();
      
      infoTimeout.current = setTimeout(() => {
        Animated.timing(fadeAnim, {
          toValue: 0,
          duration: 500,
          useNativeDriver: true,
        }).start(() => {
          setInfoVisible(false);
        });
      }, 5000);
    }
  };

  // Toggle mute
  const toggleMute = () => {
    if (videoRef.current) {
      videoRef.current.setMuted(!isMuted); // Changed from setIsMutedAsync()
      setIsMuted(!isMuted);
    }
  };

  // Toggle like
  const handleLike = async () => {
    const result = await toggleFavorite(video);
    setIsLiked(result);
  };

  // Handle video press
  const handleVideoPress = () => {
    toggleInfo();
    
    // Also toggle play/pause if tapped in the center area
    if (videoRef.current) {
      if (status.isPlaying) {
        videoRef.current.pause(); // Changed from pauseAsync()
      } else {
        videoRef.current.play(); // Changed from playAsync()
      }
    }
  };

  // Render video controls
  const renderControls = () => {
    if (!infoVisible) return null;
    
    return (
      <Animated.View 
        style={[
          styles.controlsContainer, 
          { opacity: fadeAnim }
        ]}
      >
        {/* Top info area with gradient overlay */}
        <BlurView intensity={40} style={styles.topInfo}>
          <Text style={styles.title}>{video.title}</Text>
          {video.doi && (
            <Text style={styles.doi}>DOI: {video.doi}</Text>
          )}
        </BlurView>
        
        {/* Side controls */}
        <View style={styles.sideControls}>
          <TouchableOpacity style={styles.controlButton} onPress={handleLike}>
            <Ionicons 
              name={isLiked ? "heart" : "heart-outline"} 
              size={28} 
              color={isLiked ? "#E53935" : "#fff"} 
            />
            <Text style={styles.controlText}>Like</Text>
          </TouchableOpacity>
          
          <TouchableOpacity style={styles.controlButton} onPress={onShare}>
            <Ionicons name="share-social-outline" size={28} color="#fff" />
            <Text style={styles.controlText}>Share</Text>
          </TouchableOpacity>
          
          <TouchableOpacity style={styles.controlButton} onPress={toggleMute}>
            <Ionicons 
              name={isMuted ? "volume-mute" : "volume-medium"} 
              size={28} 
              color="#fff" 
            />
            <Text style={styles.controlText}>
              {isMuted ? "Unmute" : "Mute"}
            </Text>
          </TouchableOpacity>
          
          <TouchableOpacity style={styles.controlButton} onPress={onMoreInfo}>
            <Ionicons name="information-circle-outline" size={28} color="#fff" />
            <Text style={styles.controlText}>Info</Text>
          </TouchableOpacity>
        </View>
        
        {/* Bottom caption area */}
        <BlurView intensity={40} style={styles.captionContainer}>
          <Text style={styles.captionText} numberOfLines={3}>
            {video.summary || ""}
          </Text>
          
          {video.hashtags && (
            <Text style={styles.hashtags}>{video.hashtags}</Text>
          )}
        </BlurView>
      </Animated.View>
    );
  };

  return (
    <View style={styles.container}>
      <TouchableWithoutFeedback onPress={handleVideoPress}>
        <View style={styles.videoContainer}>
          <Video
            ref={videoRef}
            source={{ uri: video.videoUrl }}
            rate={1.0}
            volume={1.0}
            isMuted={isMuted}
            resizeMode="cover"
            shouldPlay={isActive}
            isLooping
            onPlaybackStatusUpdate={status => setStatus(() => status)}
            style={styles.video}
            onLoad={() => setVideoLoaded(true)}
          />
          
          {!videoLoaded && (
            <View style={styles.loadingContainer}>
              <Ionicons name="cloud-download-outline" size={40} color="#fff" />
              <Text style={styles.loadingText}>Loading video...</Text>
            </View>
          )}
          
          {/* Progress bar */}
          {isActive && videoLoaded && (
            <VideoProgressBar 
              isActive={isActive && status.isPlaying}
              position={status.positionMillis ? status.positionMillis / 1000 : 0}
              duration={status.durationMillis ? status.durationMillis / 1000 : 0}
              style={styles.progressBar}
            />
          )}
          
          {renderControls()}
        </View>
      </TouchableWithoutFeedback>
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    width: width,
    height: height,
  },
  videoContainer: {
    flex: 1,
    backgroundColor: '#000',
    justifyContent: 'center',
  },
  video: {
    flex: 1,
  },
  loadingContainer: {
    ...StyleSheet.absoluteFillObject,
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: 'rgba(0, 0, 0, 0.3)',
  },
  loadingText: {
    color: '#fff',
    marginTop: 10,
  },
  controlsContainer: {
    ...StyleSheet.absoluteFillObject,
    justifyContent: 'space-between',
  },
  topInfo: {
    paddingTop: 60, // Account for StatusBar
    paddingHorizontal: 20,
    paddingBottom: 15,
    overflow: 'hidden',
  },
  title: {
    color: '#fff',
    fontSize: 18,
    fontWeight: 'bold',
    marginBottom: 5,
    textShadowColor: 'rgba(0, 0, 0, 0.5)',
    textShadowOffset: { width: 1, height: 1 },
    textShadowRadius: 2,
  },
  doi: {
    color: '#ddd',
    fontSize: 12,
  },
  sideControls: {
    position: 'absolute',
    right: 10,
    bottom: 120,
    alignItems: 'center',
  },
  controlButton: {
    alignItems: 'center',
    marginBottom: 20,
  },
  controlText: {
    color: '#fff',
    fontSize: 12,
    marginTop: 5,
  },
  captionContainer: {
    padding: 15,
    paddingBottom: 40, // Add extra padding at the bottom for safe area
    overflow: 'hidden',
  },
  captionText: {
    color: '#fff',
    fontSize: 14,
    marginBottom: 8,
  },
  hashtags: {
    color: '#4285F4',
    fontSize: 14,
  },
  playPauseButton: {
    position: 'absolute',
    top: '50%',
    left: '50%',
    marginLeft: -30,
    marginTop: -30,
    width: 60,
    height: 60,
    borderRadius: 30,
    backgroundColor: 'rgba(0, 0, 0, 0.5)',
    justifyContent: 'center',
    alignItems: 'center',
  },
  progressBar: {
    position: 'absolute',
    bottom: 0,
    left: 0,
    right: 0,
    height: 3,
    zIndex: 5,
  },
});

export default FullscreenVideoPlayer;