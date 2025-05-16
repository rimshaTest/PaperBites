import React, { useState, useEffect } from 'react';
import { 
  View, 
  Text, 
  StyleSheet, 
  Switch, 
  TouchableOpacity, 
  ScrollView, 
  Alert,
  SafeAreaView
} from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { getAppSettings, saveAppSettings, clearWatchHistory } from '../../services/storage';
import DebugInfo from '../../components/DebugInfo';

export default function SettingsScreen() {
  const [settings, setSettings] = useState({
    autoplay: true,
    darkMode: false,
    downloadQuality: 'medium',
    pushNotifications: true,
  });
  const [loading, setLoading] = useState(true);

  // Load settings on mount
  useEffect(() => {
    loadSettings();
  }, []);

  // Load app settings
  const loadSettings = async () => {
    try {
      const appSettings = await getAppSettings();
      setSettings(appSettings);
    } catch (error) {
      console.error('Error loading settings:', error);
    } finally {
      setLoading(false);
    }
  };

  // Update a single setting
  const updateSetting = async (key, value) => {
    try {
      const updatedSettings = { ...settings, [key]: value };
      setSettings(updatedSettings);
      await saveAppSettings(updatedSettings);
    } catch (error) {
      console.error(`Error updating ${key} setting:`, error);
    }
  };

  // Clear all app data
  const handleClearData = () => {
    Alert.alert(
      'Clear App Data',
      'This will clear your watch history, favorites, and recent searches. This action cannot be undone.',
      [
        { text: 'Cancel', style: 'cancel' },
        { 
          text: 'Clear Data', 
          style: 'destructive',
          onPress: async () => {
            try {
              await AsyncStorage.clear();
              Alert.alert('Success', 'All app data has been cleared.');
              loadSettings(); // Reload settings with defaults
            } catch (error) {
              console.error('Error clearing data:', error);
              Alert.alert('Error', 'Failed to clear app data.');
            }
          }
        }
      ]
    );
  };

  // Clear watch history
  const handleClearHistory = () => {
    Alert.alert(
      'Clear Watch History',
      'This will clear your watch history. This action cannot be undone.',
      [
        { text: 'Cancel', style: 'cancel' },
        { 
          text: 'Clear History', 
          style: 'destructive',
          onPress: async () => {
            try {
              await clearWatchHistory();
              Alert.alert('Success', 'Watch history has been cleared.');
            } catch (error) {
              console.error('Error clearing history:', error);
              Alert.alert('Error', 'Failed to clear watch history.');
            }
          }
        }
      ]
    );
  };

  // Render quality option
  const renderQualityOption = (quality, label) => (
    <TouchableOpacity
      style={[
        styles.qualityOption,
        settings.downloadQuality === quality && styles.selectedQuality
      ]}
      onPress={() => updateSetting('downloadQuality', quality)}
    >
      <Text style={[
        styles.qualityText,
        settings.downloadQuality === quality && styles.selectedQualityText
      ]}>
        {label}
      </Text>
    </TouchableOpacity>
  );

  if (loading) {
    return (
      <View style={[styles.container, styles.centered]}>
        <Ionicons name="settings" size={40} color="#ccc" />
        <Text style={styles.loadingText}>Loading settings...</Text>
      </View>
    );
  }

  return (
    <SafeAreaView style={styles.container}>
      <View style={styles.header}>
        <Text style={styles.headerTitle}>Settings</Text>
      </View>
      
      <ScrollView>
        {/* Playback Settings */}
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>Playback</Text>
          
          <View style={styles.settingRow}>
            <View style={styles.settingInfo}>
              <Text style={styles.settingTitle}>Autoplay Videos</Text>
              <Text style={styles.settingDescription}>
                Automatically play videos when scrolling
              </Text>
            </View>
            <Switch
              value={settings.autoplay}
              onValueChange={(value) => updateSetting('autoplay', value)}
              trackColor={{ false: '#d1d1d1', true: '#c1d6f8' }}
              thumbColor={settings.autoplay ? '#4285F4' : '#f5f5f5'}
            />
          </View>
          
          <View style={styles.settingRow}>
            <Text style={styles.settingTitle}>Video Quality</Text>
          </View>
          
          <View style={styles.qualityOptions}>
            {renderQualityOption('low', 'Low')}
            {renderQualityOption('medium', 'Medium')}
            {renderQualityOption('high', 'High')}
          </View>
        </View>
        
        {/* Appearance Settings */}
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>Appearance</Text>
          
          <View style={styles.settingRow}>
            <View style={styles.settingInfo}>
              <Text style={styles.settingTitle}>Dark Mode</Text>
              <Text style={styles.settingDescription}>
                Use dark theme throughout the app
              </Text>
            </View>
            <Switch
              value={settings.darkMode}
              onValueChange={(value) => updateSetting('darkMode', value)}
              trackColor={{ false: '#d1d1d1', true: '#c1d6f8' }}
              thumbColor={settings.darkMode ? '#4285F4' : '#f5f5f5'}
            />
          </View>
        </View>
        
        {/* Notification Settings */}
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>Notifications</Text>
          
          <View style={styles.settingRow}>
            <View style={styles.settingInfo}>
              <Text style={styles.settingTitle}>Push Notifications</Text>
              <Text style={styles.settingDescription}>
                Receive notifications for new content
              </Text>
            </View>
            <Switch
              value={settings.pushNotifications}
              onValueChange={(value) => updateSetting('pushNotifications', value)}
              trackColor={{ false: '#d1d1d1', true: '#c1d6f8' }}
              thumbColor={settings.pushNotifications ? '#4285F4' : '#f5f5f5'}
            />
          </View>
        </View>
        
        {/* Data Management */}
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>Data Management</Text>
          
          <TouchableOpacity 
            style={styles.dataButton}
            onPress={handleClearHistory}
          >
            <View style={styles.dataButtonTextContainer}>
              <Ionicons name="time" size={22} color="#333" />
              <Text style={styles.dataButtonText}>Clear Watch History</Text>
            </View>
            <Ionicons name="chevron-forward" size={20} color="#757575" />
          </TouchableOpacity>
          
          <TouchableOpacity 
            style={styles.dataButton}
            onPress={handleClearData}
          >
            <View style={styles.dataButtonTextContainer}>
              <Ionicons name="trash" size={22} color="#E53935" />
              <Text style={[styles.dataButtonText, styles.dangerText]}>
                Clear All App Data
              </Text>
            </View>
            <Ionicons name="chevron-forward" size={20} color="#757575" />
          </TouchableOpacity>
        </View>
        
        {/* About */}
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>About</Text>
          
          <View style={styles.aboutContainer}>
            <Text style={styles.appName}>PaperBites</Text>
            <Text style={styles.appVersion}>Version 1.0.0</Text>
            <Text style={styles.appDescription}>
              Convert research papers into short-form videos
            </Text>
          </View>
        </View>
        
        {/* Add the DebugInfo component at the bottom */}
        <DebugInfo visible={false} />
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#fff',
  },
  centered: {
    justifyContent: 'center',
    alignItems: 'center',
  },
  loadingText: {
    marginTop: 12,
    fontSize: 16,
    color: '#666',
  },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    paddingVertical: 16,
    borderBottomWidth: 1,
    borderBottomColor: '#e0e0e0',
  },
  headerTitle: {
    fontSize: 20,
    fontWeight: 'bold',
    color: '#333',
  },
  section: {
    paddingHorizontal: 16,
    paddingVertical: 12,
    borderBottomWidth: 1,
    borderBottomColor: '#e0e0e0',
  },
  sectionTitle: {
    fontSize: 16,
    fontWeight: 'bold',
    color: '#333',
    marginBottom: 12,
  },
  settingRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingVertical: 12,
  },
  settingInfo: {
    flex: 1,
  },
  settingTitle: {
    fontSize: 16,
    color: '#333',
  },
  settingDescription: {
    fontSize: 12,
    color: '#757575',
    marginTop: 4,
  },
  qualityOptions: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    paddingBottom: 8,
  },
  qualityOption: {
    paddingVertical: 8,
    paddingHorizontal: 16,
    borderRadius: 8,
    borderWidth: 1,
    borderColor: '#e0e0e0',
    backgroundColor: '#f5f5f5',
  },
  selectedQuality: {
    backgroundColor: '#4285F4',
    borderColor: '#4285F4',
  },
  qualityText: {
    fontSize: 14,
    color: '#333',
  },
  selectedQualityText: {
    color: '#fff',
    fontWeight: 'bold',
  },
  dataButton: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingVertical: 12,
    borderBottomWidth: 1,
    borderBottomColor: '#f0f0f0',
  },
  dataButtonTextContainer: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  dataButtonText: {
    fontSize: 16,
    color: '#333',
    marginLeft: 8,
  },
  dangerText: {
    color: '#E53935',
  },
  aboutContainer: {
    alignItems: 'center',
    paddingVertical: 16,
  },
  appName: {
    fontSize: 24,
    fontWeight: 'bold',
    color: '#333',
  },
  appVersion: {
    fontSize: 14,
    color: '#757575',
    marginTop: 4,
  },
  appDescription: {
    fontSize: 14,
    color: '#333',
    marginTop: 12,
    textAlign: 'center',
  },
});