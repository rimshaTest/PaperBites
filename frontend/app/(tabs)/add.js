import { Redirect } from 'expo-router';

/**
 * Placeholder screen for the center "+" tab slot (see (tabs)/_layout.tsx). Never actually
 * reached in normal use - that tab's tabPress listener always intercepts the press and pushes
 * the real /add-paper modal instead of switching to this tab - but redirects there anyway as a
 * harmless fallback in case it ever is.
 */
export default function AddTabPlaceholder() {
  return <Redirect href="/add-paper" />;
}
