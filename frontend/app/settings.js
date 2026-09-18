import React from 'react';
import { View, Text, TouchableOpacity, Switch, StyleSheet } from 'react-native';
import {SafeAreaView} from 'react-native-safe-area-context';
import { useRouter } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import { useAppSettings } from '../hooks/useStorage';
import theme from '../constants/theme';

const QUALITY_OPTIONS = ['low', 'medium', 'high'];

export default function SettingsScreen() {
  const router = useRouter();
  const { settings, loading, updateSettings } = useAppSettings();

  const cycleQuality = () => {
    const currentIndex = QUALITY_OPTIONS.indexOf(settings.downloadQuality);
    const next = QUALITY_OPTIONS[(currentIndex + 1) % QUALITY_OPTIONS.length];
    updateSettings({ downloadQuality: next });
  };

  if (loading) {
    return <SafeAreaView style={styles.container} />;
  }

  return (
    <SafeAreaView style={styles.container}>
      <View style={styles.header}>
        <TouchableOpacity onPress={() => router.back()} style={styles.backButton}>
          <Ionicons name="arrow-back" size={22} color={theme.text} />
        </TouchableOpacity>
        <Text style={styles.headerTitle}>Settings</Text>
        <View style={{ width: 22 }} />
      </View>

      <View style={styles.row}>
        <Text style={styles.rowText}>Autoplay videos</Text>
        <Switch
          value={settings.autoplay}
          onValueChange={(value) => updateSettings({ autoplay: value })}
          trackColor={{ true: theme.accent }}
        />
      </View>

      <View style={styles.row}>
        <Text style={styles.rowText}>Dark mode</Text>
        <Switch
          value={settings.darkMode}
          onValueChange={(value) => updateSettings({ darkMode: value })}
          trackColor={{ true: theme.accent }}
        />
      </View>

      <View style={styles.row}>
        <Text style={styles.rowText}>Push notifications</Text>
        <Switch
          value={settings.pushNotifications}
          onValueChange={(value) => updateSettings({ pushNotifications: value })}
          trackColor={{ true: theme.accent }}
        />
      </View>

      <TouchableOpacity style={styles.row} onPress={cycleQuality}>
        <Text style={styles.rowText}>Download quality</Text>
        <Text style={styles.rowValue}>{settings.downloadQuality}</Text>
      </TouchableOpacity>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: theme.background,
    padding: 20,
  },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    marginBottom: 24,
  },
  backButton: {
    width: 22,
  },
  headerTitle: {
    fontFamily: theme.serif,
    fontSize: 20,
    fontWeight: 'bold',
    color: theme.text,
  },
  row: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    backgroundColor: theme.surface,
    borderWidth: 1.5,
    borderColor: theme.border,
    borderRadius: 10,
    paddingHorizontal: 16,
    paddingVertical: 14,
    marginBottom: 12,
  },
  rowText: {
    fontSize: 15,
    color: theme.text,
  },
  rowValue: {
    fontSize: 14,
    color: theme.textMuted,
    textTransform: 'capitalize',
  },
});
