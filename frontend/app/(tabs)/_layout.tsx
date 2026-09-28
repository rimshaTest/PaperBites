import { Tabs, useRouter } from 'expo-router';
import React from 'react';
import { Platform, TouchableOpacity } from 'react-native';

import { HapticTab } from '../../components/HapticTab';
import { Ionicons } from '@expo/vector-icons';

import { IconSymbol } from '../../components/ui/IconSymbol';
import TabBarBackground from '../../components/ui/TabBarBackground';
import { useTheme } from '../../hooks/useTheme';

export default function TabLayout() {
  const { theme } = useTheme();
  const router = useRouter();
  return (
    <Tabs
      screenOptions={{
        tabBarActiveTintColor: theme.text,
        tabBarInactiveTintColor: theme.textMuted,
        headerShown: false,
        tabBarButton: HapticTab,
        tabBarBackground: TabBarBackground,
        tabBarStyle: Platform.select({
          // iOS gets a translucent blur (see TabBarBackground.ios.tsx) tinted to match our own
          // light/dark scheme, so it stays transparent here.
          ios: {
            position: 'absolute',
          },
          // Android/web have no blur backdrop (TabBarBackground.tsx renders nothing) and
          // otherwise fall back to React Navigation's default light background regardless of
          // theme - set it explicitly so the tab bar actually follows dark mode there too.
          default: {
            backgroundColor: theme.surface,
            borderTopColor: theme.border,
          },
        }),
      }}>
      <Tabs.Screen
        name="index"
        options={{
          title: 'Explore',
          tabBarIcon: ({ color }) => <IconSymbol size={26} name="safari.fill" color={color} />,
        }}
      />
      <Tabs.Screen
        name="visualizations"
        options={{
          title: 'Visualize',
          tabBarIcon: ({ color }) => <IconSymbol size={26} name="circle.grid.2x2.fill" color={color} />,
        }}
      />
      <Tabs.Screen
        name="add-paper"
        options={{
          tabBarIcon: ({ color }) => <IconSymbol size={26} name="plus.circle.fill" color={color} />,
        }}
      />
      <Tabs.Screen 
        name="saved" 
        options={{ 
          title: 'Saved',
          tabBarIcon: ({ color }) => <IconSymbol size={26} name="bookmark.fill" color={color} />
        }}
      />
      <TouchableOpacity onPress={() => router.push('/add-paper')} hitSlop={12}>
        <Ionicons name="add" size={26} color={theme.text} />
      </TouchableOpacity>
      {/* Reachable from Profile > Settings > Manage Feed, and shown once as an onboarding
          popup right after signup - not a tab of its own. */}
      <Tabs.Screen name="interests" options={{ href: null }} />
    </Tabs>
  );
}
