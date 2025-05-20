import * as React from 'react';
import { View, Text, StyleSheet, Platform } from 'react-native';

interface SimpleScreenProps {
  message?: string;
}

const SimpleScreen: React.FC<SimpleScreenProps> = ({ message }) => {
  return (
    <View style={styles.screenContainer}>
      <Text style={styles.messageText}>{message || "Hello World!"}</Text>
    </View>
  );
};

// Platform-specific shadow styles
const getShadowStyles = () => {
  if (Platform.OS === 'ios') {
    return {
      shadowColor: '#000',
      shadowOffset: { width: 0, height: 2 },
      shadowOpacity: 0.1,
      shadowRadius: 4,
    };
  } else if (Platform.OS === 'android') {
    return {
      elevation: 2,
    };
  } else if (Platform.OS === 'web') {
    // Use boxShadow for web
    return {
      // @ts-ignore - boxShadow is available on web but not in RN types
      boxShadow: '0px 2px 4px rgba(0, 0, 0, 0.1)',
    };
  }
  return {};
};

const styles = StyleSheet.create({
  screenContainer: {
    backgroundColor: '#ffffff',
    padding: 20,
    borderRadius: 10,
    marginVertical: 10,
    width: '80%',
    maxWidth: 400,
    alignItems: 'center',
    ...getShadowStyles(),
  },
  messageText: {
    fontSize: 18,
    color: '#333',
    textAlign: 'center',
  },
});

export default SimpleScreen;