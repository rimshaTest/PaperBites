// app/index.tsx (or similar)
import * as React from 'react';
import { StyleSheet, SafeAreaView, StatusBar, Platform } from 'react-native';
import VideoFeed from '../../components/VideoFeed'; // Adjust the path as needed

export default function HomeScreen() {
  return (
    <SafeAreaView style={styles.container}>
      <StatusBar barStyle="light-content" backgroundColor="transparent" translucent />
      <VideoFeed />
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#000',
  },
});