import React, { useState } from 'react';
import { Stack } from 'expo-router';
import { GestureHandlerRootView } from 'react-native-gesture-handler';
import { AuthProvider } from '../hooks/useAuth';
import IntroVideo from '../components/IntroVideo';

export default function Layout() {
  // The Stack (and whatever it renders underneath, e.g. Home's feed fetch) mounts immediately -
  // the intro is just a full-screen overlay on top of it, not a route of its own, so there's
  // nothing to navigate "back" out of once it finishes.
  const [showIntro, setShowIntro] = useState(true);

  return (
    <GestureHandlerRootView style={{ flex: 1 }}>
      <AuthProvider>
        <Stack screenOptions={{ headerShown: false }}>
          <Stack.Screen name="(tabs)" />
          <Stack.Screen name="login" />
          <Stack.Screen name="signup" />
          <Stack.Screen name="paper/[id]" />
          <Stack.Screen name="author/[id]" />
          <Stack.Screen name="journal/[name]" />
          <Stack.Screen name="interests-onboarding" options={{ presentation: 'modal' }} />
          <Stack.Screen name="add-paper" options={{ presentation: 'modal' }} />
          <Stack.Screen name="search" options={{ presentation: 'modal' }} />
          <Stack.Screen name="settings" />
          <Stack.Screen name="profile-details" />
        </Stack>
        {showIntro && <IntroVideo onFinish={() => setShowIntro(false)} />}
      </AuthProvider>
    </GestureHandlerRootView>
  );
}
