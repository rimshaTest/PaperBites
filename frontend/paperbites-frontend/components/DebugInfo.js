import React, { useState, useEffect } from 'react';
import { View, Text, StyleSheet, ScrollView, TouchableOpacity, Platform } from 'react-native';
import Constants from 'expo-constants';
import * as Network from 'expo-network';
import AsyncStorage from '@react-native-async-storage/async-storage';
import ApiConfig from '../constants/ApiConfig';

const DebugInfo = ({ visible = false }) => {
  const [isVisible, setIsVisible] = useState(visible);
  const [networkInfo, setNetworkInfo] = useState(null);
  const [storageKeys, setStorageKeys] = useState([]);
  const [apiTest, setApiTest] = useState({ status: 'Not tested', result: null });

  useEffect(() => {
    if (isVisible) {
      fetchDebugInfo();
    }
  }, [isVisible]);

  const fetchDebugInfo = async () => {
    try {
      // Get network info
      const networkState = await Network.getNetworkStateAsync();
      setNetworkInfo(networkState);

      // Get AsyncStorage keys
      const keys = await AsyncStorage.getAllKeys();
      setStorageKeys(keys);

      // Test API connection
      testApiConnection();
    } catch (error) {
      console.error('Error fetching debug info:', error);
    }
  };

  const testApiConnection = async () => {
    setApiTest({ status: 'Testing...', result: null });
    try {
      // Try to fetch videos endpoint
      const response = await fetch(`${ApiConfig.BASE_URL}/videos?limit=1`);
      const data = await response.json();
      setApiTest({ 
        status: response.ok ? 'Success' : 'Failed', 
        result: {
          status: response.status,
          data: data
        }
      });
    } catch (error) {
      setApiTest({ 
        status: 'Error', 
        result: {
          message: error.message,
          stack: error.stack
        }
      });
    }
  };

  if (!isVisible) {
    return (
      <TouchableOpacity 
        style={styles.showButton}
        onPress={() => setIsVisible(true)}
      >
        <Text style={styles.showButtonText}>Show Debug Info</Text>
      </TouchableOpacity>
    );
  }

  return (
    <View style={styles.container}>
      <ScrollView style={styles.scrollView}>
        <View style={styles.header}>
          <Text style={styles.headerText}>Debug Information</Text>
          <TouchableOpacity onPress={() => setIsVisible(false)}>
            <Text style={styles.closeButton}>Close</Text>
          </TouchableOpacity>
        </View>

        <View style={styles.section}>
          <Text style={styles.sectionTitle}>App Info</Text>
          <Text style={styles.infoText}>App Name: {Constants.expoConfig?.name}</Text>
          <Text style={styles.infoText}>App Version: {Constants.expoConfig?.version}</Text>
          <Text style={styles.infoText}>Expo SDK: {Constants.expoConfig?.sdkVersion}</Text>
          <Text style={styles.infoText}>Platform: {Platform.OS} {Platform.Version}</Text>
          <Text style={styles.infoText}>Is Device: {Constants.isDevice ? 'Yes' : 'No'}</Text>
        </View>

        <View style={styles.section}>
          <Text style={styles.sectionTitle}>API Configuration</Text>
          <Text style={styles.infoText}>Base URL: {ApiConfig.BASE_URL}</Text>
          <Text style={styles.infoText}>API Test Status: {apiTest.status}</Text>
          {apiTest.result && (
            <View style={styles.apiResultContainer}>
              <Text style={styles.infoText}>
                {JSON.stringify(apiTest.result, null, 2)}
              </Text>
            </View>
          )}
          <TouchableOpacity 
            style={styles.testButton}
            onPress={testApiConnection}
          >
            <Text style={styles.testButtonText}>Test API Connection</Text>
          </TouchableOpacity>
        </View>

        {networkInfo && (
          <View style={styles.section}>
            <Text style={styles.sectionTitle}>Network Info</Text>
            <Text style={styles.infoText}>
              Type: {networkInfo.type}
            </Text>
            <Text style={styles.infoText}>
              Is Connected: {networkInfo.isConnected ? 'Yes' : 'No'}
            </Text>
            <Text style={styles.infoText}>
              Is Internet Reachable: {networkInfo.isInternetReachable ? 'Yes' : 'No'}
            </Text>
          </View>
        )}

        <View style={styles.section}>
          <Text style={styles.sectionTitle}>Storage Keys</Text>
          {storageKeys.length > 0 ? (
            storageKeys.map((key, index) => (
              <Text key={index} style={styles.infoText}>{key}</Text>
            ))
          ) : (
            <Text style={styles.infoText}>No storage keys found</Text>
          )}
        </View>
      </ScrollView>
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    position: 'absolute',
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    backgroundColor: 'rgba(0,0,0,0.9)',
    zIndex: 1000,
  },
  scrollView: {
    flex: 1,
    padding: 20,
  },
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 20,
    paddingBottom: 10,
    borderBottomWidth: 1,
    borderBottomColor: '#555',
  },
  headerText: {
    fontSize: 20,
    fontWeight: 'bold',
    color: '#fff',
  },
  closeButton: {
    fontSize: 16,
    color: '#f88',
    padding: 5,
  },
  section: {
    marginBottom: 20,
    padding: 10,
    backgroundColor: 'rgba(255,255,255,0.1)',
    borderRadius: 8,
  },
  sectionTitle: {
    fontSize: 16,
    fontWeight: 'bold',
    color: '#fff',
    marginBottom: 10,
  },
  infoText: {
    fontSize: 14,
    color: '#ddd',
    marginBottom: 5,
  },
  apiResultContainer: {
    marginTop: 10,
    padding: 10,
    backgroundColor: 'rgba(0,0,0,0.3)',
    borderRadius: 5,
  },
  testButton: {
    marginTop: 10,
    backgroundColor: '#4285F4',
    padding: 10,
    borderRadius: 5,
    alignItems: 'center',
  },
  testButtonText: {
    color: '#fff',
    fontSize: 14,
    fontWeight: 'bold',
  },
  showButton: {
    position: 'absolute',
    bottom: 20,
    right: 20,
    backgroundColor: 'rgba(66, 133, 244, 0.8)',
    paddingHorizontal: 12,
    paddingVertical: 8,
    borderRadius: 20,
    zIndex: 100,
  },
  showButtonText: {
    color: '#fff',
    fontSize: 12,
  },
});

export default DebugInfo;