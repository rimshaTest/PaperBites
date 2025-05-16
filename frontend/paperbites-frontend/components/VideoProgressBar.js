// components/VideoProgressBar.js
import React, { useEffect, useRef } from 'react';
import { View, StyleSheet, Animated } from 'react-native';

const VideoProgressBar = ({ isActive, position, duration, style }) => {
  const progressAnim = useRef(new Animated.Value(0)).current;
  
  useEffect(() => {
    if (isActive && duration > 0) {
      // Calculate progress percentage
      const progress = position / duration;
      
      // Update animation value
      Animated.timing(progressAnim, {
        toValue: progress,
        duration: 250, // Update smoothly
        useNativeDriver: false,
      }).start();
    }
  }, [position, duration, isActive]);

  return (
    <View style={[styles.container, style]}>
      <Animated.View 
        style={[
          styles.progress,
          { width: progressAnim.interpolate({
              inputRange: [0, 1],
              outputRange: ['0%', '100%'],
            }) 
          }
        ]}
      />
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    width: '100%',
    height: 3,
    backgroundColor: 'rgba(255, 255, 255, 0.2)',
  },
  progress: {
    height: '100%',
    backgroundColor: '#4285F4',
  },
});

export default VideoProgressBar;