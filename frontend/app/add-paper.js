import React, { useState } from 'react';
import {
  View,
  Text,
  TextInput,
  TouchableOpacity,
  StyleSheet,
  ScrollView,
  ActivityIndicator,
  SafeAreaView,
  Alert,
} from 'react-native';
import { useRouter } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import { searchPaperByCitation, addPaperByCitation } from '../services/api';
import { useAuth } from '../hooks/useAuth';
import theme from '../constants/theme';

/**
 * Add-a-paper-by-citation flow (docs/TECHNICAL_SPEC.md's "Add-Paper Ingestion Pipeline"),
 * reached from the Saved tab's "+" button. Two steps:
 *   1. Paste a citation (MLA, APA, or any other style - sent to the backend as-is).
 *   2. Confirm which of Crossref's fuzzy-matched candidates is the right paper, then save.
 * The category isn't picked here - the backend's Gemini summary step reads the paper's
 * abstract/full text and chooses the best-fitting category in the same call, so it's
 * classified the same way a discovered-feed paper's summary is generated. On success the
 * paper is stored server-side and auto-bookmarked, so it shows up immediately in Saved.
 */
export default function AddPaperScreen() {
  const router = useRouter();
  const { token } = useAuth();

  const [citation, setCitation] = useState('');
  const [searching, setSearching] = useState(false);
  const [candidates, setCandidates] = useState(null);
  const [selected, setSelected] = useState(null);
  const [saving, setSaving] = useState(false);

  const handleSearch = async () => {
    if (!citation.trim() || !token) return;
    setSearching(true);
    setCandidates(null);
    setSelected(null);
    try {
      const results = await searchPaperByCitation(token, citation.trim());
      setCandidates(results ?? []);
    } catch (err) {
      console.error('Citation search failed:', err);
      Alert.alert('Search failed', err.message || 'Could not search for that citation. Try again.');
    } finally {
      setSearching(false);
    }
  };

  const handleSave = async (candidate) => {
    if (!candidate || !token) return;
    setSelected(candidate);
    setSaving(true);
    try {
      const paper = await addPaperByCitation(token, candidate);
      router.replace(`/paper/${paper.id}`);
    } catch (err) {
      console.error('Adding paper failed:', err);
      Alert.alert('Could not add paper', err.message || 'Something went wrong. Try again.');
      setSelected(null);
    } finally {
      setSaving(false);
    }
  };

  return (
    <SafeAreaView style={styles.container}>
      <View style={styles.header}>
        <TouchableOpacity onPress={() => router.back()} hitSlop={12}>
          <Ionicons name="close" size={26} color={theme.text} />
        </TouchableOpacity>
        <Text style={styles.headerTitle}>Add a Paper</Text>
        <View style={{ width: 26 }} />
      </View>

      <ScrollView contentContainerStyle={styles.content} keyboardShouldPersistTaps="handled">
        <Text style={styles.label}>Paste a citation (MLA, APA, or any other style)</Text>
        <TextInput
          style={styles.input}
          multiline
          placeholder={'e.g. Lovelace, Ada. "A Study of Widgets." Journal of Widgets, 2024.'}
          placeholderTextColor={theme.textMuted}
          value={citation}
          onChangeText={setCitation}
        />
        <TouchableOpacity
          style={[styles.primaryButton, !citation.trim() && styles.buttonDisabled]}
          onPress={handleSearch}
          disabled={!citation.trim() || searching}
        >
          {searching ? (
            <ActivityIndicator color={theme.surface} />
          ) : (
            <Text style={styles.primaryButtonText}>Search</Text>
          )}
        </TouchableOpacity>

        {candidates !== null && (
          <View style={styles.resultsSection}>
            <Text style={styles.sectionTitle}>
              {candidates.length === 0 ? 'No matches found' : 'Tap the right paper to add it'}
            </Text>
            {candidates.length === 0 && (
              <Text style={styles.emptyText}>
                Try pasting more of the citation, or check the title/author spelling.
              </Text>
            )}
            {candidates.map((candidate) => {
              const isSelected = selected?.doi === candidate.doi;
              return (
                <TouchableOpacity
                  key={candidate.doi}
                  style={[styles.candidateCard, isSelected && styles.candidateCardSelected]}
                  onPress={() => handleSave(candidate)}
                  disabled={saving}
                >
                  <Text style={styles.candidateTitle}>{candidate.title}</Text>
                  {candidate.authors?.length > 0 && (
                    <Text style={styles.candidateMeta}>{candidate.authors.join(', ')}</Text>
                  )}
                  <Text style={styles.candidateMeta}>
                    {[candidate.journal, candidate.published_date?.slice(0, 4)]
                      .filter(Boolean)
                      .join(' · ')}
                  </Text>
                  <View style={styles.oaBadge}>
                    {isSelected && saving ? (
                      <>
                        <ActivityIndicator size="small" color={theme.textMuted} />
                        <Text style={styles.oaBadgeText}>Adding - summarizing and categorizing...</Text>
                      </>
                    ) : (
                      <>
                        <Ionicons
                          name={candidate.is_open_access ? 'lock-open-outline' : 'lock-closed-outline'}
                          size={14}
                          color={candidate.is_open_access ? theme.text : theme.textMuted}
                        />
                        <Text style={styles.oaBadgeText}>
                          {candidate.is_open_access ? 'Open access' : 'No open-access copy found'}
                        </Text>
                      </>
                    )}
                  </View>
                </TouchableOpacity>
              );
            })}
          </View>
        )}
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: theme.background,
  },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingHorizontal: 20,
    paddingVertical: 16,
    borderBottomWidth: 1.5,
    borderBottomColor: theme.border,
    backgroundColor: theme.surface,
  },
  headerTitle: {
    fontFamily: theme.serif,
    fontSize: 20,
    fontWeight: 'bold',
    color: theme.text,
  },
  content: {
    padding: 20,
    paddingBottom: 40,
  },
  label: {
    fontSize: 14,
    color: theme.textMuted,
    marginBottom: 10,
  },
  input: {
    borderWidth: 1.5,
    borderColor: theme.border,
    borderRadius: 10,
    backgroundColor: theme.surface,
    padding: 14,
    fontSize: 15,
    color: theme.text,
    minHeight: 100,
    textAlignVertical: 'top',
  },
  primaryButton: {
    backgroundColor: theme.accent,
    borderWidth: 1.5,
    borderColor: theme.border,
    borderRadius: 10,
    height: 52,
    alignItems: 'center',
    justifyContent: 'center',
    marginTop: 16,
  },
  buttonDisabled: {
    opacity: 0.5,
  },
  primaryButtonText: {
    fontSize: 16,
    fontWeight: 'bold',
    color: theme.surface,
  },
  resultsSection: {
    marginTop: 24,
  },
  sectionTitle: {
    fontFamily: theme.serif,
    fontSize: 18,
    fontWeight: 'bold',
    color: theme.text,
    marginBottom: 12,
  },
  emptyText: {
    fontSize: 14,
    color: theme.textMuted,
  },
  candidateCard: {
    borderWidth: 1.5,
    borderColor: theme.border,
    borderRadius: 10,
    backgroundColor: theme.surface,
    padding: 14,
    marginBottom: 12,
  },
  candidateCardSelected: {
    borderColor: theme.accent,
    borderWidth: 2.5,
  },
  candidateTitle: {
    fontSize: 15,
    fontWeight: 'bold',
    color: theme.text,
    marginBottom: 4,
  },
  candidateMeta: {
    fontSize: 13,
    color: theme.textMuted,
    marginBottom: 2,
  },
  oaBadge: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
    marginTop: 6,
  },
  oaBadgeText: {
    fontSize: 12,
    color: theme.textMuted,
  },
});
