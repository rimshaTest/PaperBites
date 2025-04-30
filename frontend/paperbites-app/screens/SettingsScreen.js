import React, { useState } from 'react';
import { 
  View, 
  Text, 
  StyleSheet, 
  Switch, 
  TouchableOpacity, 
  ScrollView,
  Alert
} from 'react-native';
import { Feather } from '@expo/vector-icons';

const SettingsScreen = () => {
  const [autoplay, setAutoplay] = useState(true);
  const [downloadEnabled, setDownloadEnabled] = useState(false);
  const [darkMode, setDarkMode] = useState(true);
  const [notificationsEnabled, setNotificationsEnabled] = useState(true);
  const [dataPreferences, setDataPreferences] = useState({
    ai: true,
    biology: true,
    computerScience: true,
    physics: true,
    medicine: false,
    socialScience: false,
  });

  const toggleDataPreference = (key) => {
    setDataPreferences({
      ...dataPreferences,
      [key]: !dataPreferences[key],
    });
  };

  const handleClearCache = () => {
    Alert.alert(
      'Clear Cache',
      'This will clear all cached videos and data. Continue?',
      [
        {
          text: 'Cancel',
          style: 'cancel',
        },
        {
          text: 'Clear',
          onPress: () => {
            // Implementation for clearing cache would go here
            Alert.alert('Cache Cleared', 'All cached data has been removed.');
          },
          style: 'destructive',
        },
      ]
    );
  };

  const renderSettingItem = (
    title, 
    description, 
    value, 
    onValueChange, 
    type = 'switch'
  ) => {
    return (
      <View style={styles.settingItem}>
        <View style={styles.settingTextContainer}>
          <Text style={styles.settingTitle}>{title}</Text>
          {description && (
            <Text style={styles.settingDescription}>{description}</Text>
          )}
        </View>
        
        {type === 'switch' && (
          <Switch
            value={value}
            onValueChange={onValueChange}
            trackColor={{ false: '#767577', true: '#3498db' }}
            thumbColor={value ? '#fff' : '#f4f3f4'}
          />
        )}
        
        {type === 'button' && (
          <TouchableOpacity
            style={styles.settingButton}
            onPress={onValueChange}
          >
            <Text style={styles.settingButtonText}>{value}</Text>
          </TouchableOpacity>
        )}
      </View>
    );
  };

  return (
    <ScrollView style={styles.container}>
      <View style={styles.section}>
        <Text style={styles.sectionTitle}>Video Preferences</Text>
        
        {renderSettingItem(
          'Autoplay',
          'Play videos automatically when scrolling',
          autoplay,
          () => setAutoplay(!autoplay)
        )}
        
        {renderSettingItem(
          'Allow Downloads',
          'Save videos for offline viewing',
          downloadEnabled,
          () => setDownloadEnabled(!downloadEnabled)
        )}
        
        {renderSettingItem(
          'Dark Mode',
          'Use dark theme throughout the app',
          darkMode,
          () => setDarkMode(!darkMode)
        )}
        
        {renderSettingItem(
          'Notifications',
          'Receive updates about new papers in your areas of interest',
          notificationsEnabled,
          () => setNotificationsEnabled(!notificationsEnabled)
        )}
      </View>
      
      <View style={styles.section}>
        <Text style={styles.sectionTitle}>Research Interests</Text>
        <Text style={styles.sectionDescription}>
          Customize your feed based on research areas
        </Text>
        
        {renderSettingItem(
          'Artificial Intelligence',
          null,
          dataPreferences.ai,
          () => toggleDataPreference('ai')
        )}
        
        {renderSettingItem(
          'Biology',
          null,
          dataPreferences.biology,
          () => toggleDataPreference('biology')
        )}
        
        {renderSettingItem(
          'Computer Science',
          null,
          dataPreferences.computerScience,
          () => toggleDataPreference('computerScience')
        )}
        
        {renderSettingItem(
          'Physics',
          null,
          dataPreferences.physics,
          () => toggleDataPreference('physics')
        )}
        
        {renderSettingItem(
          'Medicine',
          null,
          dataPreferences.medicine,
          () => toggleDataPreference('medicine')
        )}
        
        {renderSettingItem(
          'Social Science',
          null,
          dataPreferences.socialScience,
          () => toggleDataPreference('socialScience')
        )}
      </View>
      
      <View style={styles.section}>
        <Text style={styles.sectionTitle}>Data Management</Text>
        
        {renderSettingItem(
          'Clear Cache',
          'Free up storage space on your device',
          'Clear',
          handleClearCache,
          'button'
        )}
      </View>
      
      <View style={styles.footer}>
        <Text style={styles.footerText}>PaperBites v0.1.0</Text>
        <Text style={styles.footerSubtext}>
          Making research accessible, one video at a time
        </Text>
      </View>
    </ScrollView>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#121212',
  },
  section: {
    padding: 16,
    borderBottomWidth: 1,
    borderBottomColor: 'rgba(255, 255, 255, 0.1)',
  },
  sectionTitle: {
    fontSize: 18,
    fontWeight: 'bold',
    color: '#fff',
    marginBottom: 8,
  },
  sectionDescription: {
    fontSize: 14,
    color: '#95a5a6',
    marginBottom: 16,
  },
  settingItem: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingVertical: 12,
    borderBottomWidth: 1,
    borderBottomColor: 'rgba(255, 255, 255, 0.05)',
  },
  settingTextContainer: {
    flex: 1,
  },
  settingTitle: {
    fontSize: 16,
    color: '#fff',
  },
  settingDescription: {
    fontSize: 12,
    color: '#95a5a6',
    marginTop: 2,
  },
  settingButton: {
    backgroundColor: '#3498db',
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: 4,
  },
  settingButtonText: {
    color: '#fff',
    fontSize: 14,
  },
  footer: {
    padding: 16,
    alignItems: 'center',
  },
  footerText: {
    color: '#95a5a6',
    fontSize: 14,
  },
  footerSubtext: {
    color: '#7f8c8d',
    fontSize: 12,
    marginTop: 4,
  },
});

export default SettingsScreen;