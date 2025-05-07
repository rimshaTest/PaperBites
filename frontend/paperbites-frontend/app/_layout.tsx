import React, { useEffect } from 'react';
import { Tabs } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import { StatusBar } from 'expo-status-bar';
import AsyncStorage from '@react-native-async-storage/async-storage';

export default function AppLayout() {
  // Initialize app data on first load
  useEffect(() => {
    const initializeApp = async () => {
      try {
        // Check if recent searches exist, if not initialize with empty array
        const recentSearches = await AsyncStorage.getItem('paperbites_recent_searches');
        if (recentSearches === null) {
          await AsyncStorage.setItem('paperbites_recent_searches', JSON.stringify([]));
        }
        
        // Check if favorites exist, if not initialize with empty array
        const favorites = await AsyncStorage.getItem('paperbites_favorite_videos');
        if (favorites === null) {
          await AsyncStorage.setItem('paperbites_favorite_videos', JSON.stringify([]));
        }
        
        // Check if watch history exists, if not initialize with empty array
        const watchHistory = await AsyncStorage.getItem('paperbites_watch_history');
        if (watchHistory === null) {
          await AsyncStorage.setItem('paperbites_watch_history', JSON.stringify([]));
        }
      } catch (error) {
        console.error('Error initializing app data:', error);
      }
    };
    
    initializeApp();
  }, []);
  
  return (
    <>
      <StatusBar style="auto" />
      <Tabs
        screenOptions={{
          tabBarActiveTintColor: '#4285F4',
          tabBarInactiveTintColor: '#757575',
          tabBarLabelStyle: {
            fontSize: 12,
            fontWeight: '500',
          },
          tabBarStyle: {
            borderTopWidth: 1,
            borderTopColor: '#e0e0e0',
            backgroundColor: '#fff',
            height: 60,
            paddingBottom: 8,
            paddingTop: 8,
          },
          headerShown: false,
        }}
      >
        <Tabs.Screen
          name="index"
          options={{
            title: 'Home',
            tabBarIcon: ({ color, size }) => (
              <Ionicons name="home" size={size} color={color} />
            ),
          }}
        />
        <Tabs.Screen
          name="topics"
          options={{
            title: 'Topics',
            tabBarIcon: ({ color, size }) => (
              <Ionicons name="grid" size={size} color={color} />
            ),
          }}
        />
        <Tabs.Screen
          name="search"
          options={{
            title: 'Search',
            tabBarIcon: ({ color, size }) => (
              <Ionicons name="search" size={size} color={color} />
            ),
          }}
        />
      </Tabs>
    </>
  );
}
