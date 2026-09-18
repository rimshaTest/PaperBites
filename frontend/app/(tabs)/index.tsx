// app/index.tsx (or similar)
import * as React from 'react';
import { StyleSheet, StatusBar } from 'react-native';
import {SafeAreaView} from 'react-native-safe-area-context';
import PaperFeed from '../../components/PaperFeed';
import theme from '../../constants/theme';

export default function HomeScreen() {
  return (
    <SafeAreaView style={styles.container}>
      <StatusBar barStyle="dark-content" backgroundColor="transparent" translucent />
      <PaperFeed />
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: theme.background,
  },
});