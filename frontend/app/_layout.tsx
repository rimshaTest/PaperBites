import { Stack } from 'expo-router';
import { AuthProvider } from '../hooks/useAuth';

export default function Layout() {
  return (
    <AuthProvider>
      <Stack screenOptions={{ headerShown: false }}>
        <Stack.Screen name="(tabs)" />
        <Stack.Screen name="login" />
        <Stack.Screen name="signup" />
        <Stack.Screen name="paper/[id]" />
      </Stack>
    </AuthProvider>
  );
}
