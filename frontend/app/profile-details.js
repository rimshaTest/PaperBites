import React, { useState, useEffect, useMemo, useRef } from 'react';
import {
  View,
  Text,
  TextInput,
  TouchableOpacity,
  StyleSheet,
  ScrollView,
  ActivityIndicator,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useRouter } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import { fetchProfile, fetchProfileOptions, saveProfileTier1, saveProfileTier2 } from '../services/api';
import Select from '../components/Select';
import PlaceAutocomplete from '../components/PlaceAutocomplete';
import {
  validateInterests,
  validateOtherField,
  validateBirthDate,
  validateDisabilityOther,
  daysInMonth,
  toIsoDate,
  fromIsoDate,
  INTERESTS_MAX_ITEMS,
  INTERESTS_MAX_TOTAL_LENGTH,
  OTHER_FIELD_MAX_LENGTH,
} from '../utils/profileValidation';
import { useAuth } from '../hooks/useAuth';
import { useTheme } from '../hooks/useTheme';

const MONTHS = [
  'January', 'February', 'March', 'April', 'May', 'June',
  'July', 'August', 'September', 'October', 'November', 'December',
];

// Which Tier 2 questions get a card, and the consent key each one stores under
const CONSENT_KEYS = ['birth_date', 'gender', 'sex', 'disability'];

// Older saves stored {status, conditions}; fold those into the single checklist so they still show
function readDisability(saved, opts) {
  if (!saved) return { conditions: [], other: '' };
  if (saved.status !== undefined) {
    if (saved.status.startsWith('No')) return { conditions: [opts.disability_none], other: '' };
    return { conditions: (saved.conditions || []).filter((c) => opts.disability_options.includes(c)), other: '' };
  }
  return { conditions: saved.conditions || [], other: saved.other || '' };
}

const EMPTY_TIER1 = {
  field_of_study: '',
  field_of_study_other: '',
  education_level: '',
  general_interests: '',
  location: '',
};

export default function ProfileDetailsScreen() {
  const router = useRouter();
  const { user, token, loading: authLoading } = useAuth();
  const { theme } = useTheme();
  const styles = useMemo(() => createStyles(theme), [theme]);

  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState(false);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [saveError, setSaveError] = useState(null);
  const [errors, setErrors] = useState({});

  // Answer sets come from the server (GET /api/profile/options) - field of study in particular
  // tracks the live paper-category list, so a new category shows up here with no app release.
  const [options, setOptions] = useState(null);

  const [tier1, setTier1] = useState(EMPTY_TIER1);
  const [gender, setGender] = useState('');
  const [sex, setSex] = useState('');
  const [birth, setBirth] = useState({ year: '', month: '', day: '' });
  const [disability, setDisability] = useState({ conditions: [], other: '' });
  const [tier2Consent, setTier2Consent] = useState({});

  const load = async () => {
    if (!token) {
      setLoading(false);
      return;
    }
    try {
      setLoading(true);
      setLoadError(false);
      const [profile, opts] = await Promise.all([fetchProfile(token), fetchProfileOptions()]);
      setOptions(opts);
      setTier1({ ...EMPTY_TIER1, ...(profile.tier1 || {}) });
      const fields = profile.tier2?.fields || {};
      setGender(fields.gender || '');
      setSex(fields.sex || '');
      setBirth(fromIsoDate(fields.birth_date));
      setDisability(readDisability(fields.disability, opts));
      setTier2Consent(profile.tier2?.consent || {});
    } catch (err) {
      console.error('Failed to load profile:', err);
      setLoadError(true);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token]);

  const touched = () => {
    setSaved(false);
    setSaveError(null);
  };

  const clearError = (key) => setErrors((prev) => (prev[key] ? { ...prev, [key]: undefined } : prev));

  const updateTier1 = (key, value) => {
    touched();
    clearError(key);
    setTier1((prev) => ({ ...prev, [key]: value }));
  };

  const updateBirth = (part, value) => {
    touched();
    clearError('birth_date');
    setBirth((prev) => {
      const next = { ...prev, [part]: value };
      // Keep the day valid if the month/year changed under it (e.g. Jan 31 -> Feb)
      if (next.year && next.month && next.day && next.day > daysInMonth(next.year, next.month)) {
        next.day = daysInMonth(next.year, next.month);
      }
      return next;
    });
  };

  const toggleConsent = (key) => {
    touched();
    setTier2Consent((prev) => ({
      ...prev,
      [key]: {
        used_for_personalization: prev[key]?.used_for_personalization || false,
        used_for_feed_relevance: !prev[key]?.used_for_feed_relevance,
      },
    }));
  };

  const isOther = tier1.field_of_study === options?.other_label;

  const validateAll = () => {
    const found = {};
    if (isOther) {
      const err = validateOtherField(tier1.field_of_study_other);
      if (err) found.field_of_study_other = err;
    }
    const interestsError = validateInterests(tier1.general_interests);
    if (interestsError) found.general_interests = interestsError;
    // Location is only valid once picked from the suggestions (the box reports '' otherwise)
    if (locationText.current.trim() && !tier1.location) found.location = 'Pick a place from the suggestions.';
    const birthError = validateBirthDate(birth, options?.min_birth_year ?? 1920);
    if (birthError) found.birth_date = birthError;
    if (disability.conditions.includes(options?.disability_other)) {
      const err = validateDisabilityOther(disability.other);
      if (err) found.disability = err;
    }
    return found;
  };

  // What the location box currently shows, so save can tell "empty" from "typed but not picked"
  const locationText = useRef('');

  const handleSave = async () => {
    if (!token) return;
    const found = validateAll();
    setErrors(found);
    if (Object.keys(found).length > 0) {
      setSaveError('Please fix the highlighted fields.');
      return;
    }

    setSaving(true);
    setSaveError(null);
    try {
      await saveProfileTier1(token, {
        field_of_study: tier1.field_of_study,
        field_of_study_other: isOther ? tier1.field_of_study_other : '',
        education_level: tier1.education_level,
        general_interests: tier1.general_interests,
        location: tier1.location,
      });
      await saveProfileTier2(
        token,
        {
          birth_date: toIsoDate(birth),
          gender,
          sex,
          disability: {
            conditions: disability.conditions,
            other: disability.conditions.includes(options.disability_other) ? disability.other : '',
          },
        },
        Object.fromEntries(CONSENT_KEYS.filter((k) => tier2Consent[k]).map((k) => [k, tier2Consent[k]]))
      );
      setSaved(true);
    } catch (err) {
      console.error('Failed to save profile:', err);
      // Show the server's per-field messages under the matching inputs
      if (err.fieldErrors && Object.keys(err.fieldErrors).length > 0) {
        setErrors((prev) => ({ ...prev, ...err.fieldErrors }));
        setSaveError('Please fix the highlighted fields.');
      } else {
        setSaveError("Couldn't save your profile. Please try again.");
      }
    } finally {
      setSaving(false);
    }
  };

  const header = (
    <View style={styles.header}>
      <TouchableOpacity onPress={() => router.back()} style={styles.headerButton}>
        <Ionicons name="arrow-back" size={24} color={theme.text} />
      </TouchableOpacity>
      <Text style={styles.headerTitle}>Profile Details</Text>
      <View style={styles.headerButton} />
    </View>
  );

  if (authLoading || (loading && token)) {
    return (
      <SafeAreaView style={styles.container}>
        <ActivityIndicator style={{ marginTop: 40 }} size="large" color={theme.text} />
      </SafeAreaView>
    );
  }

  if (!user) {
    return (
      <SafeAreaView style={styles.container}>
        {header}
        <View style={styles.centerContainer}>
          <Ionicons name="lock-closed-outline" size={40} color={theme.textMuted} />
          <Text style={styles.emptyText}>Log in to fill out your profile.</Text>
          <TouchableOpacity style={styles.loginButton} onPress={() => router.push('/login')}>
            <Text style={styles.loginButtonText}>Log In</Text>
          </TouchableOpacity>
        </View>
      </SafeAreaView>
    );
  }

  if (loadError || !options) {
    return (
      <SafeAreaView style={styles.container}>
        {header}
        <View style={styles.centerContainer}>
          <Text style={styles.emptyText}>Couldn't load your profile.</Text>
          <TouchableOpacity style={styles.loginButton} onPress={load}>
            <Text style={styles.loginButtonText}>Try Again</Text>
          </TouchableOpacity>
        </View>
      </SafeAreaView>
    );
  }

  const years = Array.from(
    { length: new Date().getFullYear() - options.min_birth_year + 1 },
    (_, i) => String(new Date().getFullYear() - i)
  );
  const monthDays = birth.year && birth.month ? daysInMonth(birth.year, birth.month) : 31;
  const days = Array.from({ length: monthDays }, (_, i) => String(i + 1));

  const consentToggle = (key) => (
    <View style={styles.consentRow}>
      <TouchableOpacity style={styles.consentToggle} onPress={() => toggleConsent(key)}>
        <Ionicons
          name={tier2Consent[key]?.used_for_feed_relevance ? 'checkbox' : 'square-outline'}
          size={20}
          color={tier2Consent[key]?.used_for_feed_relevance ? theme.accent : theme.textMuted}
        />
        <Text style={styles.consentLabel}>Personalize my feed with this</Text>
      </TouchableOpacity>
    </View>
  );

  return (
    <SafeAreaView style={styles.container}>
      {header}

      <ScrollView contentContainerStyle={styles.content} keyboardShouldPersistTaps="handled">
        <Text style={styles.disclaimer}>
          Everything below is optional. It's used only to make your feed and reading experience
          more relevant, and is kept private and pseudonymized - never shown to other users.
        </Text>

        <Text style={styles.sectionTitle}>About you</Text>
        <View style={styles.field}>
          <Text style={styles.label}>Field of study</Text>
          <Select
            title="Field of study"
            placeholder="Select a field"
            options={options.field_of_study}
            value={tier1.field_of_study}
            onChange={(v) => updateTier1('field_of_study', v)}
            error={errors.field_of_study}
          />
          {isOther && (
            <View style={styles.otherInput}>
              <TextInput
                style={[styles.input, !!errors.field_of_study_other && styles.inputError]}
                value={tier1.field_of_study_other}
                onChangeText={(v) => updateTier1('field_of_study_other', v)}
                placeholder="Your field of study"
                placeholderTextColor={theme.textMuted}
                maxLength={OTHER_FIELD_MAX_LENGTH}
                accessibilityLabel="Other field of study"
              />
              {!!errors.field_of_study_other && (
                <Text style={styles.errorText}>{errors.field_of_study_other}</Text>
              )}
            </View>
          )}
        </View>

        <View style={styles.field}>
          <Text style={styles.label}>Education level</Text>
          <Select
            title="Education level"
            placeholder="Select a level"
            options={options.education_levels}
            value={tier1.education_level}
            onChange={(v) => updateTier1('education_level', v)}
            error={errors.education_level}
          />
        </View>

        <View style={styles.field}>
          <Text style={styles.label}>General interests</Text>
          <TextInput
            style={[styles.input, !!errors.general_interests && styles.inputError]}
            value={tier1.general_interests}
            onChangeText={(v) => updateTier1('general_interests', v)}
            onBlur={() => {
              const err = validateInterests(tier1.general_interests);
              setErrors((prev) => ({ ...prev, general_interests: err || undefined }));
            }}
            placeholder="e.g. climate policy, genetics"
            placeholderTextColor={theme.textMuted}
            maxLength={INTERESTS_MAX_TOTAL_LENGTH}
            autoCorrect={false}
            accessibilityLabel="General interests"
          />
          {errors.general_interests ? (
            <Text style={styles.errorText}>{errors.general_interests}</Text>
          ) : (
            <Text style={styles.hint}>
              Separate with commas. Letters and numbers only, up to {INTERESTS_MAX_ITEMS} interests.
            </Text>
          )}
        </View>

        <View style={styles.field}>
          <Text style={styles.label}>Location</Text>
          <PlaceAutocomplete
            value={tier1.location}
            onChange={(label) => updateTier1('location', label)}
            onTextChange={(text) => {
              locationText.current = text;
            }}
            error={errors.location}
            placeholder="Start typing a city, state or country"
          />
        </View>

        <Text style={styles.sectionTitle}>Demographic Information</Text>
        <Text style={styles.sectionSubtitle}>
          Each question below has its own switch for using your answer to personalize your feed.
        </Text>

        <View style={styles.tier2Card}>
          <Text style={styles.label}>Date of birth</Text>
          <View style={styles.dateRow}>
            <Select
              compact
              title="Month"
              placeholder="Month"
              allowClear={false}
              options={MONTHS}
              value={birth.month ? MONTHS[birth.month - 1] : ''}
              onChange={(v) => updateBirth('month', MONTHS.indexOf(v) + 1)}
              error={errors.birth_date ? ' ' : undefined}
            />
            <Select
              compact
              title="Day"
              placeholder="Day"
              allowClear={false}
              options={days}
              value={birth.day ? String(birth.day) : ''}
              onChange={(v) => updateBirth('day', Number(v))}
              error={errors.birth_date ? ' ' : undefined}
            />
            <Select
              compact
              title="Year"
              placeholder="Year"
              allowClear={false}
              options={years}
              value={birth.year ? String(birth.year) : ''}
              onChange={(v) => updateBirth('year', Number(v))}
              error={errors.birth_date ? ' ' : undefined}
            />
          </View>
          {!!errors.birth_date && <Text style={styles.errorText}>{errors.birth_date}</Text>}
          {!!(birth.year || birth.month || birth.day) && (
            <TouchableOpacity
              onPress={() => {
                touched();
                clearError('birth_date');
                setBirth({ year: '', month: '', day: '' });
              }}
            >
              <Text style={styles.clearLink}>Clear date</Text>
            </TouchableOpacity>
          )}
          {consentToggle('birth_date')}
        </View>

        <View style={styles.tier2Card}>
          <Text style={styles.label}>Gender</Text>
          <Select
            title="Gender"
            placeholder="Select"
            options={options.genders}
            value={gender}
            onChange={(v) => {
              touched();
              setGender(v);
            }}
            error={errors.gender}
          />
          {consentToggle('gender')}
        </View>

        <View style={styles.tier2Card}>
          <Text style={styles.label}>Sex</Text>
          <Select
            title="Sex"
            placeholder="Select"
            options={options.sexes}
            value={sex}
            onChange={(v) => {
              touched();
              setSex(v);
            }}
            error={errors.sex}
          />
          {consentToggle('sex')}
        </View>

        <View style={styles.tier2Card}>
          <Text style={styles.label}>Disability</Text>
          <Select
            multiple
            title="Select all that apply"
            placeholder="Select all that apply"
            options={options.disability_options}
            value={disability.conditions}
            onChange={(next) => {
              touched();
              clearError('disability');
              setDisability((prev) => {
                const none = options.disability_none;
                // "None" excludes everything else: picking it clears the rest, and picking
                // anything else while it's selected drops it
                const justPickedNone = next.includes(none) && !prev.conditions.includes(none);
                const conditions = justPickedNone ? [none] : next.filter((c) => c !== none || next.length === 1);
                return { ...prev, conditions };
              });
            }}
            error={disability.conditions.includes(options.disability_other) ? undefined : errors.disability}
          />
          {disability.conditions.length > 0 && (
            <Text style={styles.hint}>
              {disability.conditions.map((c) => (c === options.disability_other ? 'Other' : c)).join('; ')}
            </Text>
          )}
          {disability.conditions.includes(options.disability_other) && (
            <View style={styles.otherInput}>
              <TextInput
                style={[styles.input, !!errors.disability && styles.inputError]}
                value={disability.other}
                onChangeText={(v) => {
                  touched();
                  clearError('disability');
                  setDisability((prev) => ({ ...prev, other: v }));
                }}
                placeholder="Describe your disability or condition"
                placeholderTextColor={theme.textMuted}
                maxLength={OTHER_FIELD_MAX_LENGTH}
                accessibilityLabel="Other disability or condition"
              />
              {!!errors.disability && <Text style={styles.errorText}>{errors.disability}</Text>}
            </View>
          )}
          {consentToggle('disability')}
        </View>

        {!!saveError && <Text style={[styles.errorText, styles.saveError]}>{saveError}</Text>}
        <TouchableOpacity style={styles.saveButton} onPress={handleSave} disabled={saving}>
          <Text style={styles.saveButtonText}>
            {saving ? 'Saving...' : saved ? 'Saved' : 'Save Profile'}
          </Text>
        </TouchableOpacity>
      </ScrollView>
    </SafeAreaView>
  );
}

const createStyles = (theme) => StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: theme.background,
  },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingHorizontal: 10,
    paddingVertical: 10,
    borderBottomWidth: 1.5,
    borderBottomColor: theme.border,
    backgroundColor: theme.surface,
  },
  headerButton: {
    width: 34,
    padding: 5,
  },
  headerTitle: {
    fontFamily: theme.serif,
    fontSize: 18,
    fontWeight: 'bold',
    color: theme.text,
  },
  content: {
    padding: 20,
    paddingBottom: 40,
  },
  disclaimer: {
    fontSize: 13,
    color: theme.textMuted,
    marginBottom: 20,
    lineHeight: 18,
  },
  sectionTitle: {
    fontFamily: theme.serif,
    fontSize: 18,
    fontWeight: 'bold',
    color: theme.text,
    marginTop: 10,
    marginBottom: 10,
  },
  sectionSubtitle: {
    fontSize: 13,
    color: theme.textMuted,
    marginBottom: 14,
  },
  field: {
    marginBottom: 14,
  },
  label: {
    fontSize: 13,
    color: theme.textMuted,
    marginBottom: 6,
  },
  input: {
    borderWidth: 1.5,
    borderColor: theme.border,
    borderRadius: 10,
    paddingHorizontal: 14,
    paddingVertical: 10,
    fontSize: 15,
    color: theme.text,
    backgroundColor: theme.surface,
  },
  tier2Card: {
    backgroundColor: theme.surface,
    borderWidth: 1.5,
    borderColor: theme.border,
    borderRadius: 10,
    padding: 14,
    marginBottom: 12,
  },
  consentRow: {
    flexDirection: 'row',
    gap: 16,
    marginTop: 10,
  },
  consentToggle: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
  },
  consentLabel: {
    fontSize: 12,
    color: theme.textMuted,
  },
  inputError: {
    borderColor: theme.danger,
  },
  otherInput: {
    marginTop: 10,
  },
  errorText: {
    color: theme.danger,
    fontSize: 12,
    marginTop: 4,
  },
  saveError: {
    marginTop: 6,
    fontSize: 13,
  },
  hint: {
    fontSize: 12,
    color: theme.textMuted,
    marginTop: 4,
    lineHeight: 16,
  },
  dateRow: {
    flexDirection: 'row',
    gap: 8,
  },
  conditions: {
    marginTop: 12,
  },
  clearLink: {
    fontSize: 12,
    color: theme.textMuted,
    textDecorationLine: 'underline',
    marginTop: 6,
  },
  saveButton: {
    backgroundColor: theme.accent,
    borderWidth: 1.5,
    borderColor: theme.border,
    borderRadius: 10,
    height: 52,
    alignItems: 'center',
    justifyContent: 'center',
    marginTop: 10,
  },
  saveButtonText: {
    fontSize: 16,
    fontWeight: 'bold',
    color: theme.surface,
  },
  centerContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    padding: 20,
  },
  emptyText: {
    fontSize: 15,
    color: theme.textMuted,
    textAlign: 'center',
    marginTop: 10,
  },
  loginButton: {
    backgroundColor: theme.accent,
    borderWidth: 1.5,
    borderColor: theme.border,
    borderRadius: 10,
    paddingVertical: 10,
    paddingHorizontal: 30,
    marginTop: 16,
  },
  loginButtonText: {
    color: theme.text,
    fontSize: 15,
    fontWeight: 'bold',
  },
});
