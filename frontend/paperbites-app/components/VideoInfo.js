import React from 'react';
import { View, Text, StyleSheet, TouchableOpacity, Linking } from 'react-native';
import { Feather } from '@expo/vector-icons';

const VideoInfo = ({ title, summary, keywords, doi, isActive }) => {
  const handleOpenPaper = () => {
    if (doi) {
      Linking.openURL(`https://doi.org/${doi}`);
    }
  };

  const renderKeywords = () => {
    if (!keywords || keywords.length === 0) return null;
    
    return (
      <View style={styles.keywordsContainer}>
        {keywords.map((keyword, index) => (
          <View key={index} style={styles.keywordBubble}>
            <Text style={styles.keywordText}>#{keyword.replace(/\s+/g, '')}</Text>
          </View>
        ))}
      </View>
    );
  };

  return (
    <View style={styles.container}>
      <View style={styles.contentContainer}>
        <Text style={styles.title} numberOfLines={2}>
          {title}
        </Text>
        
        <Text style={styles.summary} numberOfLines={3}>
          {summary}
        </Text>
        
        {renderKeywords()}
        
        {doi && (
          <TouchableOpacity 
            style={styles.paperButton} 
            onPress={handleOpenPaper}
            activeOpacity={0.8}
          >
            <Feather name="file-text" size={16} color="#fff" />
            <Text style={styles.paperButtonText}>View Original Paper</Text>
          </TouchableOpacity>
        )}
      </View>
      
      <View style={styles.sideContainer}>
        <TouchableOpacity style={styles.iconButton}>
          <Feather name="heart" size={28} color="#fff" />
          <Text style={styles.iconText}>Like</Text>
        </TouchableOpacity>
        
        <TouchableOpacity style={styles.iconButton}>
          <Feather name="share-2" size={28} color="#fff" />
          <Text style={styles.iconText}>Share</Text>
        </TouchableOpacity>
        
        <TouchableOpacity style={styles.iconButton}>
          <Feather name="bookmark" size={28} color="#fff" />
          <Text style={styles.iconText}>Save</Text>
        </TouchableOpacity>
      </View>
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    position: 'absolute',
    bottom: 0,
    left: 0,
    right: 0,
    padding: 16,
    flexDirection: 'row',
  },
  contentContainer: {
    flex: 1,
    marginRight: 60,
  },
  sideContainer: {
    alignItems: 'center',
    justifyContent: 'flex-end',
    width: 60,
  },
  title: {
    color: '#fff',
    fontSize: 18,
    fontWeight: 'bold',
    marginBottom: 8,
    textShadowColor: 'rgba(0, 0, 0, 0.75)',
    textShadowOffset: { width: 1, height: 1 },
    textShadowRadius: 3,
  },
  summary: {
    color: '#fff',
    fontSize: 14,
    marginBottom: 12,
    textShadowColor: 'rgba(0, 0, 0, 0.75)',
    textShadowOffset: { width: 1, height: 1 },
    textShadowRadius: 3,
  },
  keywordsContainer: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    marginBottom: 12,
  },
  keywordBubble: {
    backgroundColor: 'rgba(52, 152, 219, 0.8)',
    borderRadius: 16,
    paddingHorizontal: 10,
    paddingVertical: 4,
    marginRight: 6,
    marginBottom: 6,
  },
  keywordText: {
    color: '#fff',
    fontSize: 12,
    fontWeight: '500',
  },
  paperButton: {
    backgroundColor: 'rgba(22, 160, 133, 0.8)',
    borderRadius: 20,
    paddingVertical: 8,
    paddingHorizontal: 12,
    flexDirection: 'row',
    alignItems: 'center',
    alignSelf: 'flex-start',
  },
  paperButtonText: {
    color: '#fff',
    fontSize: 12,
    fontWeight: '500',
    marginLeft: 6,
  },
  iconButton: {
    alignItems: 'center',
    marginBottom: 16,
  },
  iconText: {
    color: '#fff',
    fontSize: 12,
    marginTop: 4,
    textShadowColor: 'rgba(0, 0, 0, 0.75)',
    textShadowOffset: { width: 1, height: 1 },
    textShadowRadius: 3,
  },
});

export default VideoInfo;