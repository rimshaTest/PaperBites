import { Stack, useRouter, useSegments } from 'expo-router';
import * as React from 'react';
import { GestureHandlerRootView } from 'react-native-gesture-handler';
import { getAuth } from '../services/storage';

export default function Layout() {
  const router = useRouter();
  const segments = useSegments();
  const [checkedAuth, setCheckedAuth] = React.useState(false);

  React.useEffect(() => {
    const checkAuth = async () => {
      const session = await getAuth();
      const onLoginScreen = segments[0] === 'login';
      if (!session && !onLoginScreen) {
        router.replace('/login');
      }
      setCheckedAuth(true);
    };
    checkAuth();
    // Only run once on mount - login.js itself handles moving past this screen.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  if (!checkedAuth) {
    return null;
  }

  return (
    <GestureHandlerRootView style={{ flex: 1 }}>
      <Stack>
        <Stack.Screen name="(tabs)" options={{ headerShown: false }} />
        <Stack.Screen name="login" options={{ headerShown: false }} />
        <Stack.Screen name="settings" options={{ headerShown: false }} />
        <Stack.Screen name="author/[id]" options={{ headerShown: false }} />
        <Stack.Screen name="journal/[name]" options={{ headerShown: false }} />
        <Stack.Screen name="chat/[id]" options={{ headerShown: false }} />
      </Stack>
    </GestureHandlerRootView>
  );
}
