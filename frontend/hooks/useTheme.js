import React, { createContext, useContext, useState, useEffect, useMemo, useCallback } from 'react';
import { Appearance } from 'react-native';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { lightTheme, darkTheme } from '../constants/theme';

const STORAGE_KEY = 'paperbites_theme_preference'; // 'light' | 'dark' | 'system'

const ThemeContext = createContext(null);

/**
 * App-wide dark mode. Defaults to following the OS appearance ('system'), but the user can pin
 * light or dark from Settings; the choice is persisted so it survives app restarts. Every screen
 * reads colors through useTheme() rather than importing constants/theme.js directly, so a
 * preference change (or the OS switching at sunset) repaints the whole app immediately.
 */
export const ThemeProvider = ({ children }) => {
  const [preference, setPreference] = useState('system');
  const [systemScheme, setSystemScheme] = useState(Appearance.getColorScheme() || 'light');

  useEffect(() => {
    let cancelled = false;
    AsyncStorage.getItem(STORAGE_KEY)
      .then((stored) => {
        if (!cancelled && stored) setPreference(stored);
      })
      .catch(() => {});

    const subscription = Appearance.addChangeListener(({ colorScheme }) => {
      setSystemScheme(colorScheme || 'light');
    });
    return () => {
      cancelled = true;
      subscription.remove();
    };
  }, []);

  const scheme = preference === 'system' ? systemScheme : preference;
  const theme = useMemo(() => (scheme === 'dark' ? darkTheme : lightTheme), [scheme]);

  const setThemePreference = useCallback((pref) => {
    setPreference(pref);
    AsyncStorage.setItem(STORAGE_KEY, pref).catch(() => {});
  }, []);

  const value = useMemo(
    () => ({ theme, scheme, preference, setThemePreference }),
    [theme, scheme, preference, setThemePreference]
  );

  return <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>;
};

/**
 * @typedef {{mode: string, background: string, surface: string, text: string, textMuted: string, border: string, accent: string, danger: string, serif: string}} Theme
 * @returns {{theme: Theme, scheme: 'light'|'dark', preference: 'light'|'dark'|'system', setThemePreference: (pref: string) => void}}
 */
export const useTheme = () => {
  const context = useContext(ThemeContext);
  if (!context) {
    throw new Error('useTheme must be used within a ThemeProvider');
  }
  return context;
};
