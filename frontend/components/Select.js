import React, { useMemo, useState } from 'react';
import {
  View,
  Text,
  Modal,
  FlatList,
  Pressable,
  StyleSheet,
  useWindowDimensions,
} from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { useTheme } from '../hooks/useTheme';

/**
 * A dropdown that looks and behaves the same on web, iOS and Android (React Native has no
 * built-in <select>): a field showing the current value that opens a modal list of options.
 *
 * Single mode: tapping an option picks it and closes. Multi mode (`multiple`): options toggle
 * and a Done button closes. `allowClear` adds a "Not specified" row for single mode, since
 * every profile field is optional.
 *
 * Props: value (string, or string[] in multi mode), options (string[]), onChange, placeholder,
 * title (modal heading), error (message shown under the field), disabled, testID.
 */
export default function Select({
  value,
  options,
  onChange,
  placeholder = 'Select',
  title,
  multiple = false,
  allowClear = true,
  error,
  disabled = false,
  testID,
  compact = false,
}) {
  const { theme } = useTheme();
  const styles = useMemo(() => createStyles(theme), [theme]);
  const { width, height } = useWindowDimensions();
  const [open, setOpen] = useState(false);

  const selected = multiple ? value || [] : value ? [value] : [];
  const display = multiple
    ? selected.length
      ? `${selected.length} selected`
      : ''
    : value || '';

  const close = () => setOpen(false);

  const handlePick = (option) => {
    if (multiple) {
      onChange(selected.includes(option) ? selected.filter((o) => o !== option) : [...selected, option]);
    } else {
      onChange(option);
      close();
    }
  };

  const rows = !multiple && allowClear && value ? ['', ...options] : options;

  return (
    <View style={compact ? styles.compactWrap : undefined}>
      <Pressable
        testID={testID}
        accessibilityRole="button"
        accessibilityLabel={title || placeholder}
        disabled={disabled}
        onPress={() => setOpen(true)}
        style={[styles.field, !!error && styles.fieldError, disabled && styles.fieldDisabled]}
      >
        <Text
          style={[styles.fieldText, !display && styles.placeholder]}
          numberOfLines={1}
        >
          {display || placeholder}
        </Text>
        <Ionicons name="chevron-down" size={18} color={theme.textMuted} />
      </Pressable>
      {!!error && <Text style={styles.errorText}>{error}</Text>}

      <Modal visible={open} transparent animationType="fade" onRequestClose={close}>
        <Pressable style={styles.backdrop} onPress={close}>
          {/* The inner Pressable swallows taps so touching the sheet doesn't dismiss it */}
          <Pressable
            style={[styles.sheet, { maxHeight: height * 0.7, width: Math.min(width - 32, 480) }]}
            onPress={() => {}}
          >
            {!!title && <Text style={styles.sheetTitle}>{title}</Text>}
            <FlatList
              data={rows}
              keyExtractor={(item, index) => `${item}-${index}`}
              renderItem={({ item }) => {
                const isClear = item === '';
                const isSelected = !isClear && selected.includes(item);
                return (
                  <Pressable
                    accessibilityRole="menuitem"
                    onPress={() => (isClear ? (onChange(''), close()) : handlePick(item))}
                    style={[styles.row, isSelected && styles.rowSelected]}
                  >
                    {multiple && (
                      <Ionicons
                        name={isSelected ? 'checkbox' : 'square-outline'}
                        size={20}
                        color={isSelected ? theme.accent : theme.textMuted}
                      />
                    )}
                    <Text style={[styles.rowText, isClear && styles.clearText]}>
                      {isClear ? 'Not specified' : item}
                    </Text>
                    {!multiple && isSelected && (
                      <Ionicons name="checkmark" size={18} color={theme.accent} />
                    )}
                  </Pressable>
                );
              }}
            />
            {multiple && (
              <Pressable style={styles.doneButton} onPress={close}>
                <Text style={styles.doneText}>Done</Text>
              </Pressable>
            )}
          </Pressable>
        </Pressable>
      </Modal>
    </View>
  );
}

const createStyles = (theme) =>
  StyleSheet.create({
    compactWrap: { flex: 1 },
    field: {
      flexDirection: 'row',
      alignItems: 'center',
      justifyContent: 'space-between',
      gap: 8,
      borderWidth: 1.5,
      borderColor: theme.border,
      borderRadius: 10,
      paddingHorizontal: 14,
      paddingVertical: 12,
      backgroundColor: theme.surface,
    },
    fieldError: { borderColor: theme.danger },
    fieldDisabled: { opacity: 0.5 },
    fieldText: { flex: 1, fontSize: 15, color: theme.text },
    placeholder: { color: theme.textMuted },
    errorText: { color: theme.danger, fontSize: 12, marginTop: 4 },
    backdrop: {
      flex: 1,
      backgroundColor: 'rgba(0,0,0,0.45)',
      alignItems: 'center',
      justifyContent: 'center',
    },
    sheet: {
      backgroundColor: theme.background,
      borderRadius: 14,
      borderWidth: 1.5,
      borderColor: theme.border,
      paddingVertical: 8,
      overflow: 'hidden',
    },
    sheetTitle: {
      fontFamily: theme.serif,
      fontSize: 16,
      fontWeight: 'bold',
      color: theme.text,
      paddingHorizontal: 16,
      paddingVertical: 10,
    },
    row: {
      flexDirection: 'row',
      alignItems: 'center',
      gap: 10,
      paddingHorizontal: 16,
      paddingVertical: 12,
    },
    rowSelected: { backgroundColor: theme.surface },
    rowText: { flex: 1, fontSize: 15, color: theme.text },
    clearText: { color: theme.textMuted, fontStyle: 'italic' },
    doneButton: {
      margin: 12,
      alignItems: 'center',
      paddingVertical: 12,
      borderRadius: 10,
      backgroundColor: theme.accent,
      borderWidth: 1.5,
      borderColor: theme.border,
    },
    doneText: { fontWeight: 'bold', color: theme.onAccent },
  });
