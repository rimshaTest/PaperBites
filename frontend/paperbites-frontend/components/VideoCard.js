// components/VideoCard.js
import React from 'react';
import { 
  View, 
  Text, 
  StyleSheet, 
  TouchableOpacity, 
  ImageBackground 
} from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { formatDate } from '../utils/formatters';

const VideoCard = ({ 
  video, 
  onPress, 
  compact = false,
  showWatchDate = false
}) => {
  // Generate a thumbnail URL or use a placeholder
  const thumbnailUrl = video.thumbnailUrl || 'https://via.placeholder.com/300x200?text=Video';
  
  return (
    <TouchableOpacity 
      style={[styles.container, compact && styles.compactContainer]}
      onPress={onPress}
      activeOpacity={0.8}
    >
      <ImageBackground
        source={{ uri: thumbnailUrl }}
        style={styles.thumbnail}
        imageStyle={styles.thumbnailImage}
      >
        <View style={styles.duration}>
          <Ionicons name="play" size={14} color="#fff" />
        </View>
      </ImageBackground>
      
      <View style={styles.infoContainer}>
        <Text 
          style={styles.title} 
          numberOfLines={compact ? 1 : 2}
        >
          {video.title}
        </Text>
        
        {showWatchDate && video.watchedAt && (
          <Text style={styles.watchDate}>
            Watched on {formatDate(video.watchedAt / 1000)}
          </Text>
        )}
      </View>
    </TouchableOpacity>
  );
};

const styles = StyleSheet.create({
  container: {
    margin: 8,
    backgroundColor: '#fff',
    borderRadius: 8,
    overflow: 'hidden',
    elevation: 2,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.2,
    shadowRadius: 2,
  },
  compactContainer: {
    flex: 0.5,
    marginHorizontal: 4,
  },
  thumbnail: {
    height: 150,
    justifyContent: 'flex-end',
    alignItems: 'flex-end',
  },
  thumbnailImage: {
    borderTopLeftRadius: 8,
    borderTopRightRadius: 8,
  },
  duration: {
    backgroundColor: 'rgba(0,0,0,0.7)',
    paddingHorizontal: 8,
    paddingVertical: 4,
    borderRadius: 4,
    margin: 8,
    flexDirection: 'row',
    alignItems: 'center',
  },
  infoContainer: {
    padding: 12,
  },
  title: {
    fontSize: 14,
    fontWeight: 'bold',
    color: '#333',
  },
  watchDate: {
    fontSize: 12,
    color: '#757575',
    marginTop: 4,
  }
});

export default VideoCard;