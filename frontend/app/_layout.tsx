import { Stack } from 'expo-router';
import { GestureHandlerRootView } from 'react-native-gesture-handler';
import { AuthProvider } from '../hooks/useAuth';

export default function Layout() {
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
          <Stack.Screen name="settings" />
          <Stack.Screen name="profile-details" />
        </Stack>
      </AuthProvider>
    </GestureHandlerRootView>
  );
}
