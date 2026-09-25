import React, { useEffect, useRef, useState } from 'react';
import {
  View,
  Text,
  TextInput,
  TouchableOpacity,
  Pressable,
  StyleSheet,
  ScrollView,
  ActivityIndicator,
  SafeAreaView,
  Alert,
  Platform,
} from 'react-native';
import { useRouter } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import * as ImagePicker from 'expo-image-picker';
import {
  searchPaperByCitation,
  addPaperByCitation,
  submitPaperForReview,
  scanPaperPhoto,
} from '../services/api';
import { useAuth } from '../hooks/useAuth';
import theme from '../constants/theme';

/**
 * Add-a-paper-by-citation flow (docs/TECHNICAL_SPEC.md's "Add-Paper Ingestion Pipeline"),
 * reached from the Saved tab's "+" button. Two steps:
 *   1. Paste a citation (MLA, APA, or any other style), a direct link to the paper's page
 *      (e.g. an open-access journal's article URL), or - experimentally - a photo of the
 *      paper's title page/a poster via the camera button, which Gemini vision reads into a
 *      citation string server-side. Either way it's resolved into candidate matches.
 *   2. Confirm which of the resolved candidates is the right paper, then save.
 * The category isn't picked here - the backend's Gemini summary step reads the paper's
 * abstract/full text and chooses the best-fitting category in the same call, so it's
 * classified the same way a discovered-feed paper's summary is generated. On success the
 * paper is stored server-side and auto-bookmarked, so it shows up immediately in Saved.
 *
 * If nothing matches, the user can submit the input for manual admin review instead of being
 * stuck - the spec's fallback for when automated matching can't resolve something.
 */
export default function AddPaperScreen() {
  const router = useRouter();
  const { token } = useAuth();

  const [citation, setCitation] = useState('');
  const [searching, setSearching] = useState(false);
  const [scanning, setScanning] = useState(false);
  const [candidates, setCandidates] = useState(null);
  const [selected, setSelected] = useState(null);
  const [saving, setSaving] = useState(false);
  const [submittingReview, setSubmittingReview] = useState(false);
  const [reviewSubmitted, setReviewSubmitted] = useState(false);
  const [showExperimentalTip, setShowExperimentalTip] = useState(false);
  const tooltipTimeoutRef = useRef(null);

  useEffect(() => {
    return () => {
      if (tooltipTimeoutRef.current) clearTimeout(tooltipTimeoutRef.current);
    };
  }, []);

  const handleSearch = async () => {
    if (!citation.trim() || !token) return;
    setSearching(true);
    setCandidates(null);
    setSelected(null);
    setReviewSubmitted(false);
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

  const handleToggleExperimentalTip = () => {
    setShowExperimentalTip(true);
    if (tooltipTimeoutRef.current) clearTimeout(tooltipTimeoutRef.current);
    // No hover-out on a touch device to dismiss it, so auto-hide shortly after a tap.
    tooltipTimeoutRef.current = setTimeout(() => setShowExperimentalTip(false), 2200);
  };

  const handleHideExperimentalTip = () => {
    if (tooltipTimeoutRef.current) clearTimeout(tooltipTimeoutRef.current);
    setShowExperimentalTip(false);
  };

  const handleScanImage = async (asset) => {
    if (!token || !asset) return;
    setScanning(true);
    setCandidates(null);
    setSelected(null);
    setReviewSubmitted(false);
    try {
      const result = await scanPaperPhoto(token, { uri: asset.uri, mimeType: asset.mimeType });
      setCitation(result.extracted || '');
      setCandidates(result.candidates ?? []);
      if (!result.extracted) {
        Alert.alert(
          "Couldn't read that photo",
          "We couldn't make out a title in that photo. Try a clearer, well-lit shot, or type/paste the citation instead."
        );
      }
    } catch (err) {
      console.error('Photo scan failed:', err);
      Alert.alert('Scan failed', err.message || 'Could not process that photo. Try again.');
    } finally {
      setScanning(false);
    }
  };

  const handleTakePhoto = async () => {
    const permission = await ImagePicker.requestCameraPermissionsAsync();
    if (!permission.granted) {
      Alert.alert('Camera permission needed', 'Enable camera access in Settings to use this feature.');
      return;
    }
    const result = await ImagePicker.launchCameraAsync({ quality: 0.7 });
    if (!result.canceled) {
      await handleScanImage(result.assets[0]);
    }
  };

  const handleChoosePhoto = async () => {
    const permission = await ImagePicker.requestMediaLibraryPermissionsAsync();
    if (!permission.granted) {
      Alert.alert('Photo library permission needed', 'Enable photo access in Settings to use this feature.');
      return;
    }
    const result = await ImagePicker.launchImageLibraryAsync({
      mediaTypes: ImagePicker.MediaTypeOptions.Images,
      quality: 0.7,
    });
    if (!result.canceled) {
      await handleScanImage(result.assets[0]);
    }
  };

  const handlePickImage = () => {
    if (scanning) return;
    Alert.alert(
      'Add from a photo (experimental)',
      "Take a picture of the paper's title page or a poster, or choose a screenshot from your library.",
      [
        { text: 'Take Photo', onPress: handleTakePhoto },
        { text: 'Choose from Library', onPress: handleChoosePhoto },
        { text: 'Cancel', style: 'cancel' },
      ]
    );
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

  const handleSubmitForReview = async () => {
    if (!citation.trim() || !token) return;
    setSubmittingReview(true);
    try {
      await submitPaperForReview(token, citation.trim());
      setReviewSubmitted(true);
    } catch (err) {
      console.error('Submitting for review failed:', err);
      Alert.alert('Could not submit', err.message || 'Something went wrong. Try again.');
    } finally {
      setSubmittingReview(false);
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
        <Text style={styles.label}>
          Paste a citation (MLA, APA, or any other style) or a link to the paper's page
        </Text>
        <View style={styles.inputRow}>
          <TextInput
            style={[styles.input, styles.inputFlex]}
            multiline
            placeholder={
              'e.g. Lovelace, Ada. "A Study of Widgets." Journal of Widgets, 2024.\n' +
              'or https://journals.plos.org/plosone/article?id=...'
            }
            placeholderTextColor={theme.textMuted}
            value={citation}
            onChangeText={setCitation}
            autoCapitalize="none"
            autoCorrect={false}
          />
          <View style={styles.cameraButtonWrap}>
            <TouchableOpacity
              style={styles.cameraButton}
              onPress={handlePickImage}
              disabled={scanning}
            >
              {scanning ? (
                <ActivityIndicator size="small" color={theme.text} />
              ) : (
                <Ionicons name="camera-outline" size={22} color={theme.text} />
              )}
            </TouchableOpacity>
            <Pressable
              style={styles.starBadge}
              onPress={handleToggleExperimentalTip}
              {...(Platform.OS === 'web'
                ? { onHoverIn: () => setShowExperimentalTip(true), onHoverOut: handleHideExperimentalTip }
                : {})}
              hitSlop={10}
            >
              <Ionicons name="star" size={10} color={theme.surface} />
            </Pressable>
            {showExperimentalTip && (
              <View style={styles.tooltip} pointerEvents="none">
                <Text style={styles.tooltipText}>Experimental feature</Text>
              </View>
            )}
          </View>
        </View>
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
              <>
                <Text style={styles.emptyText}>
                  Try pasting more of the citation, double-check the title/author spelling, or
                  paste a direct link to the paper's page instead.
                </Text>
                {reviewSubmitted ? (
                  <Text style={styles.reviewSubmittedText}>
                    Submitted - we'll take a look and try to add it.
                  </Text>
                ) : (
                  <TouchableOpacity
                    style={[styles.secondaryButton, submittingReview && styles.buttonDisabled]}
                    onPress={handleSubmitForReview}
                    disabled={submittingReview}
                  >
                    {submittingReview ? (
                      <ActivityIndicator color={theme.text} />
                    ) : (
                      <Text style={styles.secondaryButtonText}>Submit for manual review</Text>
                    )}
                  </TouchableOpacity>
                )}
              </>
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
  inputRow: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    gap: 10,
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
  inputFlex: {
    flex: 1,
  },
  cameraButtonWrap: {
    position: 'relative',
  },
  cameraButton: {
    width: 52,
    height: 52,
    borderRadius: 10,
    borderWidth: 1.5,
    borderColor: theme.border,
    backgroundColor: theme.surface,
    alignItems: 'center',
    justifyContent: 'center',
  },
  starBadge: {
    position: 'absolute',
    top: -6,
    right: -6,
    width: 18,
    height: 18,
    borderRadius: 9,
    backgroundColor: theme.accent,
    borderWidth: 1.5,
    borderColor: theme.background,
    alignItems: 'center',
    justifyContent: 'center',
  },
  tooltip: {
    position: 'absolute',
    top: -34,
    right: -12,
    backgroundColor: theme.text,
    borderRadius: 6,
    paddingHorizontal: 8,
    paddingVertical: 5,
    zIndex: 10,
  },
  tooltipText: {
    color: theme.surface,
    fontSize: 11,
    fontWeight: 'bold',
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
  secondaryButton: {
    borderWidth: 1.5,
    borderColor: theme.border,
    borderRadius: 10,
    height: 48,
    alignItems: 'center',
    justifyContent: 'center',
    marginTop: 16,
  },
  secondaryButtonText: {
    fontSize: 15,
    fontWeight: 'bold',
    color: theme.text,
  },
  reviewSubmittedText: {
    fontSize: 14,
    color: theme.text,
    fontWeight: 'bold',
    marginTop: 16,
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
