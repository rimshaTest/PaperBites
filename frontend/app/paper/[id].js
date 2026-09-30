import React, { useState, useEffect, useMemo } from 'react';
import {
  View,
  Text,
  Image,
  StyleSheet,
  ScrollView,
  TouchableOpacity,
  Share,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useLocalSearchParams, useRouter } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import * as WebBrowser from 'expo-web-browser';
import LoadingIndicator from '../../components/LoadingIndicator';
import ErrorMessage from '../../components/ErrorMessage';
import ReadConfirmationModal from '../../components/ReadConfirmationModal';
import { fetchPaperById } from '../../services/api';
import { useFavoritePapers } from '../../hooks/useStorage';
import { useAuth } from '../../hooks/useAuth';
import { useTheme } from '../../hooks/useTheme';
import { useLike } from '../../hooks/useLike';
import { useConfirmRead } from '../../hooks/useConfirmRead';

export default function PaperDetailScreen() {
  const router = useRouter();
  const { id } = useLocalSearchParams();
  const { user, token } = useAuth();
  const { theme } = useTheme();
  const styles = useMemo(() => createStyles(theme), [theme]);
  const { isFavorite: isFavoriteFn, toggleFavorite: toggleFavoriteFn } = useFavoritePapers(token);
  const [paper, setPaper] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [confirmingRead, setConfirmingRead] = useState(false);
  const [justConfirmedRead, setJustConfirmedRead] = useState(false);
  const { liked, count: likeCount, toggle: toggleLike } = useLike(token, paper);
  const confirmRead = useConfirmRead();

  useEffect(() => {
    const loadPaper = async () => {
      try {
        setLoading(true);
        const data = await fetchPaperById(id, token);
        setPaper(data);
      } catch (err) {
        setError(`Failed to load paper: ${err.message}`);
      } finally {
        setLoading(false);
      }
    };

    if (id) {
      loadPaper();
    }
  }, [id, token]);

  const isFavorite = isFavoriteFn(id);

  const toggleFavorite = async () => {
    if (!user) {
      router.push('/login');
      return;
    }
    if (paper) {
      await toggleFavoriteFn(paper);
    }
  };

  const handleShare = async () => {
    if (!paper) return;
    try {
      await Share.share({
        message: `${paper.title}${paper.url ? `\n${paper.url}` : ''}`,
        title: paper.title,
      });
    } catch (error) {
      console.error('Error sharing paper:', error);
    }
  };

  const handleOpenLink = async () => {
    if (!paper?.url) return;

    // Opens an in-app browser (SFSafariViewController/Chrome Custom Tabs) rather than handing
    // off to a fully separate app via Linking.openURL - that keeps this screen's JS alive the
    // whole time, and openBrowserAsync's promise resolves deterministically the instant the user
    // closes it, which is what actually makes "did you read this paper?" reliable: no dependency
    // on AppState ever noticing a background/foreground transition (which is what the previous,
    // unreliable version of this feature depended on).
    await WebBrowser.openBrowserAsync(paper.url);

    // Only signed-in users get the Libby-style prompt, since the graph/stats are account-scoped
    // like bookmarks.
    if (token) {
      setConfirmingRead(true);
    }
  };

  const handleConfirmRead = async () => {
    if (!token) {
      router.push('/login');
      return;
    }
    await confirmRead(token, paper.id);
    setJustConfirmedRead(true);
  };

  const handleAuthorPress = (author) => {
    router.push(`/author/${encodeURIComponent(author.id)}`);
  };

  const handleJournalPress = (journal) => {
    router.push(`/journal/${encodeURIComponent(journal)}`);
  };

  if (loading) {
    return <LoadingIndicator message="Loading paper..." />;
  }

  if (error || !paper) {
    return (
      <ErrorMessage
        message={error || 'Paper not found'}
        onBack={() => router.back()}
      />
    );
  }

  const authors = paper.authors || [];

  return (
    <SafeAreaView style={styles.container}>
      <View style={styles.header}>
        <TouchableOpacity onPress={() => router.back()} style={styles.headerButton}>
          <Ionicons name="arrow-back" size={24} color={theme.text} />
        </TouchableOpacity>

        <View style={styles.headerActions}>
          <TouchableOpacity onPress={toggleFavorite} style={styles.headerButton}>
            <Ionicons
              name={isFavorite ? 'bookmark' : 'bookmark-outline'}
              size={24}
              color={isFavorite ? theme.accent : theme.text}
            />
          </TouchableOpacity>

          <TouchableOpacity onPress={toggleLike} style={styles.headerButton}>
            <Ionicons
              name={liked ? 'heart' : 'heart-outline'}
              size={24}
              color={liked ? theme.like : theme.text}
            />
          </TouchableOpacity>

          <TouchableOpacity onPress={handleShare} style={styles.headerButton}>
            <Ionicons name="share-outline" size={24} color={theme.text} />
          </TouchableOpacity>
        </View>
      </View>

      <ScrollView style={styles.detailsContainer}>
        {paper.image_url && (
          <Image source={{ uri: paper.image_url }} style={styles.heroImage} resizeMode="cover" />
        )}

        <Text style={styles.title}>{paper.title}</Text>

        {authors.length > 0 && (
          <Text style={styles.authors}>
            {authors.map((author, index) => (
              <Text
                key={author.id || author.name}
                onPress={author.id ? () => handleAuthorPress(author) : undefined}
                style={author.id ? styles.link : undefined}
              >
                {author.name}{index < authors.length - 1 ? ', ' : ''}
              </Text>
            ))}
          </Text>
        )}

        {(paper.journal || paper.published_date) && (
          <Text style={styles.meta}>
            {paper.journal ? (
              <Text onPress={() => handleJournalPress(paper.journal)} style={styles.link}>
                {paper.journal}
              </Text>
            ) : null}
            {paper.journal && paper.published_date ? ' · ' : ''}
            {paper.published_date || ''}
          </Text>
        )}

        {paper.doi && (
          <View style={styles.infoRow}>
            <Text style={styles.infoText}>DOI: {paper.doi}</Text>
          </View>
        )}

        <View style={styles.section}>
          <Text style={styles.sectionTitle}>Summary</Text>
          <Text style={styles.description}>{paper.description || paper.abstract}</Text>
        </View>

        {paper.categories && paper.categories.length > 0 && (
          <View style={styles.section}>
            <Text style={styles.sectionTitle}>Categories</Text>
            <View style={styles.categoriesContainer}>
              {paper.categories.map((category, index) => (
                <View key={index} style={styles.categoryChip}>
                  <Text style={styles.categoryText}>{category}</Text>
                </View>
              ))}
            </View>
          </View>
        )}

        {paper.url && (
          <>
            <TouchableOpacity style={styles.linkButton} onPress={handleOpenLink}>
              <Text style={styles.linkButtonText}>View Original Paper</Text>
            </TouchableOpacity>
            {!!paper.read_count && (
              <View style={styles.readCountRow}>
                <Ionicons name="people" size={14} color={theme.textMuted} />
                <Text style={styles.readCountText}>
                  {paper.read_count} {paper.read_count === 1 ? 'person has' : 'people have'} read this
                </Text>
              </View>
            )}
          </>
        )}

        <TouchableOpacity
          style={[styles.confirmReadButton, justConfirmedRead && styles.confirmReadButtonDone]}
          onPress={handleConfirmRead}
          disabled={justConfirmedRead}
        >
          <Ionicons
            name={justConfirmedRead ? 'checkmark-circle' : 'checkmark-circle-outline'}
            size={18}
            color={justConfirmedRead ? theme.accent : theme.text}
          />
          <Text style={styles.confirmReadButtonText}>
            {justConfirmedRead ? "You've read this!" : "Have you read this?"}
          </Text>
        </TouchableOpacity>
      </ScrollView>

      <ReadConfirmationModal
        visible={confirmingRead}
        paper={paper}
        token={token}
        onDismiss={() => setConfirmingRead(false)}
      />
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
    padding: 5,
    borderRadius: 20,
  },
  headerActions: {
    flexDirection: 'row',
  },
  detailsContainer: {
    flex: 1,
    padding: 20,
  },
  heroImage: {
    width: '100%',
    height: 200,
    borderRadius: 10,
    marginBottom: 16,
    backgroundColor: theme.surface,
  },
  link: {
    color: theme.accent,
    textDecorationLine: 'underline',
  },
  title: {
    fontFamily: theme.serif,
    fontSize: 22,
    fontWeight: 'bold',
    marginBottom: 8,
    color: theme.text,
  },
  authors: {
    fontSize: 14,
    color: theme.textMuted,
    marginBottom: 4,
  },
  meta: {
    fontSize: 13,
    color: theme.textMuted,
    marginBottom: 12,
  },
  infoRow: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 15,
  },
  infoText: {
    fontSize: 14,
    color: theme.textMuted,
    marginLeft: 5,
  },
  section: {
    marginBottom: 20,
  },
  sectionTitle: {
    fontSize: 16,
    fontWeight: 'bold',
    marginBottom: 8,
    color: theme.text,
  },
  description: {
    fontSize: 14,
    lineHeight: 20,
    color: theme.text,
  },
  categoriesContainer: {
    flexDirection: 'row',
    flexWrap: 'wrap',
  },
  categoryChip: {
    backgroundColor: theme.surface,
    borderWidth: 1,
    borderColor: theme.border,
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: 16,
    marginRight: 8,
    marginBottom: 8,
  },
  categoryText: {
    fontSize: 13,
    color: theme.text,
  },
  linkButton: {
    backgroundColor: theme.accent,
    borderWidth: 1.5,
    borderColor: theme.border,
    borderRadius: 10,
    paddingVertical: 14,
    alignItems: 'center',
    marginTop: 10,
    marginBottom: 30,
  },
  linkButtonText: {
    fontSize: 15,
    fontWeight: 'bold',
    color: theme.text,
  },
  readCountRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 6,
    marginTop: -18,
    marginBottom: 20,
  },
  readCountText: {
    fontSize: 12,
    color: theme.textMuted,
  },
  confirmReadButton: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 8,
    borderWidth: 1.5,
    borderColor: theme.border,
    borderRadius: 10,
    paddingVertical: 12,
    marginBottom: 30,
  },
  confirmReadButtonDone: {
    borderColor: theme.accent,
  },
  confirmReadButtonText: {
    fontSize: 14,
    fontWeight: '600',
    color: theme.text,
  },
});
