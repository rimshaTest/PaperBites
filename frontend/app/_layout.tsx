import { Stack } from 'expo-router';
import { AuthProvider } from '../hooks/useAuth';

export default function Layout() {
  return (
    <AuthProvider>
      <Stack />
    </AuthProvider>
  );
}
