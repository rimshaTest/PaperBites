import React from 'react';
import { View, ActivityIndicator, Text, StyleSheet } from 'react-native';
import { useTheme } from '../hooks/useTheme';

const LoadingIndicator = ({ message = 'Loading...' }) => {
  const { theme } = useTheme();
  return (
    <View style={styles.container}>
      <ActivityIndicator size="large" color={theme.accent} />
      <Text style={[styles.message, { color: theme.textMuted }]}>{message}</Text>
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    padding: 20,
  },
  message: {
    marginTop: 10,
    fontSize: 16,
    textAlign: 'center',
  },
});

export default LoadingIndicator;