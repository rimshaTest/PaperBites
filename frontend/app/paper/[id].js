import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  Image,
  StyleSheet,
  ScrollView,
  TouchableOpacity,
  Share,
  Linking,
  SafeAreaView
} from 'react-native';
import { useLocalSearchParams, useRouter } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import LoadingIndicator from '../../components/LoadingIndicator';
import ErrorMessage from '../../components/ErrorMessage';
import { fetchPaperById, recordPaperView } from '../../services/api';
import { useFavoritePapers } from '../../hooks/useStorage';
import { useAuth } from '../../hooks/useAuth';
import theme from '../../constants/theme';

export default function PaperDetailScreen() {
  const router = useRouter();
  const { id } = useLocalSearchParams();
  const { user, token } = useAuth();
  const { isFavorite: isFavoriteFn, toggleFavorite: toggleFavoriteFn } = useFavoritePapers(token);
  const [paper, setPaper] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const loadPaper = async () => {
      try {
        setLoading(true);
        const data = await fetchPaperById(id);
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
  }, [id]);

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

  const handleOpenLink = () => {
    if (paper?.url) {
      Linking.openURL(paper.url);
      // Feeds the Visualizations tab's bubble map - fire-and-forget, only for signed-in users
      // since the graph is account-scoped like bookmarks.
      if (token) {
        recordPaperView(token, paper.id);
      }
    }
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
            <Ionicons name="link-outline" size={16} color={theme.textMuted} />
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
          <TouchableOpacity style={styles.linkButton} onPress={handleOpenLink}>
            <Text style={styles.linkButtonText}>View Original Paper</Text>
          </TouchableOpacity>
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
    backgroundColor: '#f0f0f0',
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
});
