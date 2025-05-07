import React from 'react';
import { View, Text, Image, StyleSheet, TouchableOpacity, Dimensions } from 'react-native';
import Colors from '../constants/Colors';

const { width } = Dimensions.get('window');
const CARD_WIDTH = width * 0.9;

const VideoCard = ({ video, onPress }) => {
  // Extract video thumbnail from the videoUrl
  // For this demo, we'll use a placeholder image
  const thumbnailUrl = video.thumbnailUrl || 'https://via.placeholder.com/400x600';
  
  // Format paper details
  const formatDOI = (doi) => {
    return doi ? `DOI: ${doi}` : '';
  };

  return (
    <TouchableOpacity 
      style={styles.container} 
      activeOpacity={0.8}
      onPress={() => onPress(video)}
    >
      <Image 
        source={{ uri: thumbnailUrl }} 
        style={styles.thumbnail}
        resizeMode="cover"
      />
      <View style={styles.infoContainer}>
        <Text style={styles.title} numberOfLines={2}>{video.title}</Text>
        <Text style={styles.summary} numberOfLines={2}>{video.summary}</Text>
        
        {video.doi && (
          <Text style={styles.doi}>{formatDOI(video.doi)}</Text>
        )}
        
        {video.keywords && video.keywords.length > 0 && (
          <View style={styles.keywordsContainer}>
            {video.keywords.slice(0, 3).map((keyword, index) => (
              <View key={index} style={styles.keywordChip}>
                <Text style={styles.keywordText}>{keyword}</Text>
              </View>
            ))}
            {video.keywords.length > 3 && (
              <Text style={styles.moreKeywords}>+{video.keywords.length - 3}</Text>
            )}
          </View>
        )}
      </View>
    </TouchableOpacity>
  );
};

const styles = StyleSheet.create({
  container: {
    width: CARD_WIDTH,
    marginHorizontal: width * 0.05,
    marginVertical: 10,
    borderRadius: 10,
    backgroundColor: '#fff',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
    elevation: 2,
    overflow: 'hidden',
  },
  thumbnail: {
    width: '100%',
    height: 200,
    backgroundColor: '#f0f0f0',
  },
  infoContainer: {
    padding: 12,
  },
  title: {
    fontSize: 18,
    fontWeight: 'bold',
    marginBottom: 6,
    color: '#333',
  },
  summary: {
    fontSize: 14,
    color: '#666',
    marginBottom: 8,
  },
  doi: {
    fontSize: 12,
    color: '#888',
    marginBottom: 8,
  },
  keywordsContainer: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    marginTop: 5,
  },
  keywordChip: {
    backgroundColor: '#f0f0f0',
    paddingHorizontal: 8,
    paddingVertical: 4,
    borderRadius: 16,
    marginRight: 6,
    marginBottom: 6,
  },
  keywordText: {
    fontSize: 12,
    color: '#666',
  },
  moreKeywords: {
    fontSize: 12,
    color: '#666',
    alignSelf: 'center',
  },
});

export default VideoCard;