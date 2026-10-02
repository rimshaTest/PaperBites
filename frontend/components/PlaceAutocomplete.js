import React, { useEffect, useMemo, useRef, useState } from 'react';
import { View, Text, TextInput, Pressable, StyleSheet, ActivityIndicator } from 'react-native';
import { useTheme } from '../hooks/useTheme';
import { searchPlaces } from '../services/api';
import { isAlphabeticPlace } from '../utils/profileValidation';

const DEBOUNCE_MS = 250;

/**
 * Location input with city / region / country suggestions (served by the backend's offline place
 * index, GET /api/places/autocomplete). The value is only "valid" once the user picks a
 * suggestion - free-typed text that doesn't match a place is rejected, so what gets saved is
 * always a real place the server can resolve.
 *
 * Props: value (the picked label, or ''), onChange(label) - called with the label on pick and
 * with '' when the user clears the field; onTextChange(text) reports whatever is typed (so the
 * parent can tell an empty box from typed-but-not-picked); error; placeholder.
 */
export default function PlaceAutocomplete({ value, onChange, onTextChange, error, placeholder }) {
  const { theme } = useTheme();
  const styles = useMemo(() => createStyles(theme), [theme]);
  const [text, setText] = useState(value || '');
  const [suggestions, setSuggestions] = useState([]);
  const [loading, setLoading] = useState(false);
  const [typedError, setTypedError] = useState(null);
  // Set when the suggestions service can't be reached; the text is then accepted as typed
  const [unavailable, setUnavailable] = useState(false);
  const requestId = useRef(0);

  // Show the saved place when it loads in from outside. Only non-empty values sync: typing
  // reports '' upward (un-picking the place), and that must not wipe what's being typed.
  useEffect(() => {
    if (value) {
      setText(value);
      if (onTextChange) onTextChange(value);
    }
  }, [value]);

  const handleChange = (next) => {
    setText(next);
    if (onTextChange) onTextChange(next);
    setTypedError(null);
    // Typing again un-picks the previous place until a new one is chosen - unless suggestions
    // are down, in which case the typed text itself is the value.
    onChange(unavailable && isAlphabeticPlace(next) ? next.trim() : '');

    if (next.trim().length < 2) {
      setSuggestions([]);
      return;
    }
    if (!isAlphabeticPlace(next)) {
      setSuggestions([]);
      setTypedError('Use letters only.');
      return;
    }

    const id = ++requestId.current;
    setLoading(true);
    setTimeout(async () => {
      if (id !== requestId.current) return; // a newer keystroke superseded this one
      try {
        const places = await searchPlaces(next.trim());
        if (id === requestId.current) setSuggestions(places);
      } catch (err) {
        if (id === requestId.current) {
          setSuggestions([]);
          setUnavailable(true);
          onChange(isAlphabeticPlace(next) ? next.trim() : '');
        }
      } finally {
        if (id === requestId.current) setLoading(false);
      }
    }, DEBOUNCE_MS);
  };

  const handlePick = (place) => {
    requestId.current++;
    setText(place.label);
    setSuggestions([]);
    setLoading(false);
    setTypedError(null);
    onChange(place.label);
  };

  const showUnpicked = !unavailable && !!text.trim() && !value && !loading && suggestions.length === 0 && !typedError;
  const message = error || typedError || (showUnpicked && text.trim().length >= 2 ? 'Pick a place from the suggestions.' : null);

  return (
    <View>
      <View>
        <TextInput
          style={[styles.input, !!message && styles.inputError]}
          value={text}
          onChangeText={handleChange}
          placeholder={placeholder}
          placeholderTextColor={theme.textMuted}
          autoCapitalize="words"
          autoCorrect={false}
          maxLength={60}
          accessibilityLabel="Location"
        />
        {loading && <ActivityIndicator style={styles.spinner} size="small" color={theme.textMuted} />}
      </View>
      {!!message && <Text style={styles.errorText}>{message}</Text>}
      {unavailable && !message && (
        <Text style={styles.noteText}>Suggestions are unavailable right now - your text will be saved as typed.</Text>
      )}
      {suggestions.length > 0 && (
        <View style={styles.list}>
          {suggestions.map((place) => (
            <Pressable
              key={place.label}
              style={styles.item}
              onPress={() => handlePick(place)}
              accessibilityRole="menuitem"
            >
              <Text style={styles.itemText}>{place.label}</Text>
              <Text style={styles.itemType}>{place.type}</Text>
            </Pressable>
          ))}
        </View>
      )}
    </View>
  );
}

const createStyles = (theme) =>
  StyleSheet.create({
    input: {
      borderWidth: 1.5,
      borderColor: theme.border,
      borderRadius: 10,
      paddingHorizontal: 14,
      paddingVertical: 10,
      paddingRight: 40,
      fontSize: 15,
      color: theme.text,
      backgroundColor: theme.surface,
    },
    inputError: { borderColor: theme.danger },
    spinner: { position: 'absolute', right: 12, top: 12 },
    errorText: { color: theme.danger, fontSize: 12, marginTop: 4 },
    noteText: { color: theme.textMuted, fontSize: 12, marginTop: 4 },
    list: {
      marginTop: 6,
      borderWidth: 1.5,
      borderColor: theme.border,
      borderRadius: 10,
      backgroundColor: theme.background,
      overflow: 'hidden',
    },
    item: {
      flexDirection: 'row',
      alignItems: 'center',
      justifyContent: 'space-between',
      gap: 8,
      paddingHorizontal: 14,
      paddingVertical: 11,
      borderBottomWidth: StyleSheet.hairlineWidth,
      borderBottomColor: theme.border,
    },
    itemText: { flex: 1, fontSize: 14, color: theme.text },
    itemType: { fontSize: 11, color: theme.textMuted, textTransform: 'capitalize' },
  });
