import React from 'react';
import { StyleSheet, Text, View, Platform, StatusBar, SafeAreaView, ScrollView } from 'react-native';
import SimpleScreen from '../../components/SimpleScreen';
import VideoPlayer from '../../components/VideoPlayer';

export default function HomeScreen() {
  // Cloudinary URL for the video
  const videoUrl = 'https://res.cloudinary.com/dd9tsotfz/video/upload/v1747714786/qxnh1k1beqclxqdmem9g.mp4';

  return (
    <SafeAreaView style={styles.container}>
      <StatusBar barStyle="default" />
      <ScrollView contentContainerStyle={styles.scrollContent}>
        <View style={styles.content}>
          <Text style={styles.title}>Welcome to SimpleApp</Text>
          <Text style={styles.subtitle}>Running on {Platform.OS}</Text>
          
          <SimpleScreen message="This is a component!" />
          
          <Text style={styles.videoTitle}>S3 Video Player</Text>
          <VideoPlayer videoUrl={videoUrl} />
          
          <Text style={styles.description}>
            This is a minimal cross-platform app that works on web, iOS, and Android.
            The video above is loaded directly from an Amazon S3 bucket.
          </Text>
        </View>
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#f0f0f0',
  },
  scrollContent: {
    flexGrow: 1,
  },
  content: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    padding: 20,
  },
  title: {
    fontSize: 24,
    fontWeight: 'bold',
    marginBottom: 10,
    color: '#333',
  },
  subtitle: {
    fontSize: 18,
    marginBottom: 20,
    color: '#0066cc',
  },
  videoTitle: {
    fontSize: 20,
    fontWeight: 'bold',
    marginTop: 20,
    marginBottom: 10,
    color: '#333',
  },
  description: {
    fontSize: 16,
    textAlign: 'center',
    color: '#666',
    maxWidth: 400,
    marginTop: 20,
  },
});