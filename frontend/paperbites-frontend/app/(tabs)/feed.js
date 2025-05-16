// app/feed.js
import React from 'react';
import { View, StyleSheet } from 'react-native';
import { useLocalSearchParams } from 'expo-router';
import FullscreenFeed from '../../components/FullscreenFeed';

export default function FeedScreen() {
  const { videoId } = useLocalSearchParams();
  
  return (
    <View style={styles.container}>
      <FullscreenFeed initialVideoId={videoId} />
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#000',
  },
});