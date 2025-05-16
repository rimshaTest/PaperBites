// app/_layout.js
import { Redirect, Stack } from 'expo-router';
import { StatusBar } from 'expo-status-bar';

export default function AppLayout() {
  return (
    <>
      <StatusBar style="auto" />
      <Stack screenOptions={{ headerShown: false }}>
        <Stack.Screen name="(tabs)" />
        <Stack.Screen 
          name="video/[id]" 
          options={{
            presentation: "card",
            animation: "slide_from_right"
          }}
        />
      </Stack>
    </>
  );
}