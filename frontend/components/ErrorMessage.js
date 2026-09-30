import React from 'react';
import { View, Text, StyleSheet, TouchableOpacity } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { useTheme } from '../hooks/useTheme';

const ErrorMessage = ({ 
  message = 'Something went wrong', 
  onRetry = null,
  onBack = null 
}) => {
  const { theme } = useTheme();
  return (
    <View style={styles.container}>
      <Ionicons name="alert-circle-outline" size={60} color={theme.danger} />
      <Text style={[styles.message, { color: theme.text }]}>{message}</Text>
      
      <View style={styles.buttonsContainer}>
        {onRetry && (
          <TouchableOpacity style={[styles.button, { backgroundColor: theme.accent }]} onPress={onRetry}>
            <Ionicons name="refresh" size={18} color={theme.onAccent} />
            <Text style={[styles.buttonText, { color: theme.onAccent }]}>Try Again</Text>
          </TouchableOpacity>
        )}
        
        {onBack && (
          <TouchableOpacity 
            style={[styles.button, { backgroundColor: theme.textMuted }]} 
            onPress={onBack}
          >
            <Ionicons name="arrow-back" size={18} color={theme.onAccent} />
            <Text style={[styles.buttonText, { color: theme.onAccent }]}>Go Back</Text>
          </TouchableOpacity>
        )}
      </View>
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
    marginTop: 15,
    fontSize: 16,
    textAlign: 'center',
    marginBottom: 20,
  },
  buttonsContainer: {
    flexDirection: 'row',
    marginTop: 10,
  },
  button: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 15,
    paddingVertical: 10,
    borderRadius: 5,
    marginHorizontal: 5,
  },
  buttonText: {
    fontSize: 14,
    marginLeft: 5,
  },
});

export default ErrorMessage;