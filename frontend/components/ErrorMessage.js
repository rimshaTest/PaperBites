import React from 'react';
import { View, Text, StyleSheet, TouchableOpacity } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import Colors from '../constants/Colors';

const ErrorMessage = ({ 
  message = 'Something went wrong', 
  onRetry = null,
  onBack = null 
}) => {
  return (
    <View style={styles.container}>
      <Ionicons name="alert-circle-outline" size={60} color="#E53935" />
      <Text style={styles.message}>{message}</Text>
      
      <View style={styles.buttonsContainer}>
        {onRetry && (
          <TouchableOpacity style={styles.button} onPress={onRetry}>
            <Ionicons name="refresh" size={18} color="#fff" />
            <Text style={styles.buttonText}>Try Again</Text>
          </TouchableOpacity>
        )}
        
        {onBack && (
          <TouchableOpacity 
            style={[styles.button, styles.backButton]} 
            onPress={onBack}
          >
            <Ionicons name="arrow-back" size={18} color="#fff" />
            <Text style={styles.buttonText}>Go Back</Text>
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
    color: '#333',
    textAlign: 'center',
    marginBottom: 20,
  },
  buttonsContainer: {
    flexDirection: 'row',
    marginTop: 10,
  },
  button: {
    backgroundColor: '#4285F4',
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 15,
    paddingVertical: 10,
    borderRadius: 5,
    marginHorizontal: 5,
  },
  backButton: {
    backgroundColor: '#757575',
  },
  buttonText: {
    color: '#fff',
    fontSize: 14,
    marginLeft: 5,
  },
});

export default ErrorMessage;