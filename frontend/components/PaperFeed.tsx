// components/PaperFeed.tsx
import * as React from 'react';
import {
  View,
  FlatList,
  ScrollView,
  Dimensions,
  StyleSheet,
  Text,
  ActivityIndicator,
  TouchableOpacity,
  Linking,
} from 'react-native';
import Animated, {
  useSharedValue,
  useAnimatedStyle,
  withTiming,
  runOnJS,
} from 'react-native-reanimated';
import { Gesture, GestureDetector } from 'react-native-gesture-handler';
import { Image } from 'expo-image';
import { useRouter, useFocusEffect } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import { fetchPapers } from '../services/api';
import { useAuth } from '../hooks/useAuth';
import { useFavoritePapers } from '../hooks/useStorage';
import theme from '../constants/theme';

const { width, height } = Dimensions.get('window');

// The card rests showing only its bottom portion (image visible above it); dragging the handle
// up slides it over the full screen, covering the image. Only once fully expanded does its
// content become scrollable - while collapsed, dragging elsewhere still pages between papers.
const COLLAPSED_TOP = height * 0.42;
const EXPANDED_TOP = 0;

interface Author {
  id: string | null;
  name: string;
}

export interface PaperItem {
  id: string;
  title: string;
  authors: Author[];
  description: string;
  citation_count: number;
  published_date: string | null;
  journal: string | null;
  publication_type: string | null;
  is_open_access: boolean | null;
  image_url: string | null;
  url: string | null;
  doi: string | null;
  categories: string[] | null;
  language: string;
}

export const PaperCard: React.FC<{
  item: PaperItem;
  onExpandedChange: (expanded: boolean) => void;
  isBookmarked: boolean;
  onToggleBookmark: (item: PaperItem) => void;
}> = ({ item, onExpandedChange, isBookmarked, onToggleBookmark }) => {
  const router = useRouter();
  const top = useSharedValue(COLLAPSED_TOP);
  const [isExpanded, setIsExpanded] = React.useState(false);

  const setExpanded = React.useCallback(
    (expanded: boolean) => {
      setIsExpanded(expanded);
      onExpandedChange(expanded);
    },
    [onExpandedChange]
  );

  const goToAuthor = (author: Author) => {
    if (author.id) {
      router.push(`/author/${encodeURIComponent(author.id)}`);
    }
  };

  const goToJournal = () => {
    if (item.journal) {
      router.push(`/journal/${encodeURIComponent(item.journal)}` as any);
    }
  };

  const panGesture = Gesture.Pan()
    .onUpdate((event) => {
      const base = isExpanded ? EXPANDED_TOP : COLLAPSED_TOP;
      const next = base + event.translationY;
      top.value = Math.min(COLLAPSED_TOP, Math.max(EXPANDED_TOP, next));
    })
    .onEnd((event) => {
      const shouldExpand = top.value < COLLAPSED_TOP / 2 || event.velocityY < -500;
      const target = shouldExpand ? EXPANDED_TOP : COLLAPSED_TOP;
      top.value = withTiming(target, { duration: 220 });
      runOnJS(setExpanded)(shouldExpand);
    });

  const animatedCardStyle = useAnimatedStyle(() => ({
    top: top.value,
  }));

  return (
    <View style={styles.card}>
      <View style={styles.imageContainer}>
        {item.image_url ? (
          <Image source={{ uri: item.image_url }} style={styles.image} contentFit="cover" />
        ) : (
          <View style={[styles.image, styles.imageFallback]} />
        )}
        <TouchableOpacity style={styles.saveButton} onPress={() => onToggleBookmark(item)}>
          <Ionicons
            name={isBookmarked ? 'bookmark' : 'bookmark-outline'}
            size={20}
            color={isBookmarked ? theme.accent : theme.surface}
          />
        </TouchableOpacity>
        <View style={styles.badgeColumn}>
          {item.categories && item.categories.length > 0 && (
            <View style={styles.categoryBadge}>
              <Text style={styles.categoryBadgeText}>{item.categories[0]}</Text>
            </View>
          )}
          <View style={styles.languageBadge}>
            <Text style={styles.categoryBadgeText}>{item.language}</Text>
          </View>
        </View>
      </View>

      <Animated.View style={[styles.infoCard, animatedCardStyle]}>
        <GestureDetector gesture={panGesture}>
          <View style={styles.dragHandleArea}>
            <View style={styles.dragHandle} />
            <Ionicons
              name={isExpanded ? 'chevron-down' : 'chevron-up'}
              size={16}
              color={theme.textMuted}
            />
          </View>
        </GestureDetector>

        <ScrollView
          style={styles.infoCardScroll}
          contentContainerStyle={styles.infoCardContent}
          scrollEnabled={isExpanded}
          nestedScrollEnabled
          showsVerticalScrollIndicator={false}
        >
          <Text style={styles.title}>{item.title}</Text>

          {item.published_date && (
            <Text style={styles.dateText}>Published {item.published_date}</Text>
          )}

          <View style={styles.authorsRow}>
            {item.authors.length === 0 ? (
              <Text style={styles.authorsText}>Unknown authors</Text>
            ) : (
              <Text style={styles.authorsText}>
                {item.authors.map((author, index) => (
                  <React.Fragment key={`${author.id ?? author.name}-${index}`}>
                    <Text
                      style={author.id ? styles.authorLink : styles.authorPlain}
                      onPress={author.id ? () => goToAuthor(author) : undefined}
                    >
                      {author.name}
                    </Text>
                    {index < item.authors.length - 1 && <Text style={styles.authorsText}>, </Text>}
                  </React.Fragment>
                ))}
              </Text>
            )}
          </View>

          <View style={styles.statsRow}>
            <View style={styles.statItem}>
              <Ionicons name="git-branch-outline" size={16} color={theme.text} />
              <Text style={styles.statValue}>{item.citation_count}</Text>
              <Text style={styles.statLabel}>Citations</Text>
            </View>
            {item.journal && (
              <TouchableOpacity style={styles.journalPill} onPress={goToJournal}>
                <Text style={styles.journalText}>
                  {item.journal}
                  {item.publication_type ? ` · ${item.publication_type === 'conference' ? 'Conference' : 'Journal'}` : ''}
                </Text>
              </TouchableOpacity>
            )}
          </View>

          {item.doi && (
            <View style={styles.metaRow}>
              <Text
                style={styles.metaLink}
                onPress={() => Linking.openURL(`https://doi.org/${item.doi}`)}
              >
                DOI: {item.doi}
              </Text>
            </View>
          )}

          <Text style={styles.description}>{item.description}</Text>

          <View style={styles.actionRow}>
            {item.url && (
              <TouchableOpacity
                style={[styles.readButton, styles.actionButton]}
                onPress={() => Linking.openURL(item.url!)}
              >
                <Text style={styles.readButtonText}>Read paper</Text>
                <Ionicons name="open-outline" size={16} color={theme.surface} />
              </TouchableOpacity>
            )}
          </View>
        </ScrollView>
      </Animated.View>
    </View>
  );
};

const PaperFeed: React.FC = () => {
  const router = useRouter();
  const { user, token } = useAuth();
  const { isFavorite, toggleFavorite } = useFavoritePapers(token);
  const [papers, setPapers] = React.useState<PaperItem[]>([]);
  const [loading, setLoading] = React.useState(true);
  const [error, setError] = React.useState<string | null>(null);
  const [anyExpanded, setAnyExpanded] = React.useState(false);

  // Fetch papers from the backend - passing the token lets the server hard-filter to the
  // signed-in user's chosen interests (see /api/interests), when they've set any.
  useFocusEffect(
    React.useCallback(() => {
      const loadPapers = async () => {
        try {
          setLoading(true);
          const papersData = await fetchPapers({ token });
          const allPapers: PaperItem[] = papersData ?? [];
          // Sort newest to oldest (defensive - the backend already sorts, but this holds
          // regardless of query order).
          const sorted = [...allPapers].sort((a, b) =>
            (b.published_date ?? '').localeCompare(a.published_date ?? '')
          );
          setPapers(sorted);
          setError(null);
        } catch (err) {
          setError('Failed to load papers');
          console.error(err);
        } finally {
          setLoading(false);
        }
      };

      loadPapers();
    }, [token])
  );

  const handleToggleBookmark = (item: PaperItem) => {
    if (!user) {
      router.push('/login');
      return;
    }
    toggleFavorite(item as any);
  };

  if (loading) {
    return (
      <View style={styles.centerContainer}>
        <ActivityIndicator size="large" color={theme.text} />
        <Text style={styles.loadingText}>Loading papers...</Text>
      </View>
    );
  }

  if (error) {
    return (
      <View style={styles.centerContainer}>
        <Text style={styles.errorText}>{error}</Text>
      </View>
    );
  }

  if (papers.length === 0) {
    return (
      <View style={styles.centerContainer}>
        <Text style={styles.messageText}>No papers found</Text>
      </View>
    );
  }

  return (
    <FlatList
      data={papers}
      keyExtractor={(item) => item.id}
      renderItem={({ item }) => (
        <PaperCard
          item={item}
          onExpandedChange={setAnyExpanded}
          isBookmarked={isFavorite(item.id)}
          onToggleBookmark={handleToggleBookmark}
        />
      )}
      pagingEnabled
      scrollEnabled={!anyExpanded}
      snapToInterval={height}
      snapToAlignment="start"
      decelerationRate="fast"
      showsVerticalScrollIndicator={false}
      initialNumToRender={2}
      maxToRenderPerBatch={3}
      windowSize={5}
      removeClippedSubviews
      style={styles.list}
    />
  );
};

const styles = StyleSheet.create({
  list: {
    flex: 1,
    backgroundColor: theme.background,
  },
  card: {
    height,
    width,
    backgroundColor: theme.background,
    overflow: 'hidden',
  },
  imageContainer: {
    position: 'absolute',
    top: 0,
    left: 0,
    right: 0,
    height,
  },
  image: {
    width: '100%',
    height: '100%',
  },
  imageFallback: {
    backgroundColor: '#ccc4ae',
  },
  badgeColumn: {
    position: 'absolute',
    top: 50,
    right: 16,
    alignItems: 'flex-end',
    gap: 8,
  },
  categoryBadge: {
    backgroundColor: theme.accent,
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: 16,
  },
  languageBadge: {
    backgroundColor: theme.background,
    borderWidth: 1,
    borderColor: theme.accent,
    paddingHorizontal: 8,
    paddingVertical: 2,
    borderRadius: 10,
  },
  categoryBadgeText: {
    fontSize: 12,
    fontWeight: 'bold',
    color: theme.text,
    textTransform: 'capitalize',
  },
  infoCard: {
    position: 'absolute',
    left: 0,
    right: 0,
    height,
    backgroundColor: theme.background,
    borderTopLeftRadius: 24,
    borderTopRightRadius: 24,
  },
  dragHandleArea: {
    alignItems: 'center',
    paddingVertical: 10,
    gap: 4,
  },
  dragHandle: {
    width: 40,
    height: 4,
    borderRadius: 2,
    backgroundColor: theme.border,
    opacity: 0.4,
  },
  infoCardScroll: {
    flex: 1,
  },
  infoCardContent: {
    paddingHorizontal: 20,
    paddingBottom: 40,
  },
  title: {
    fontFamily: theme.serif,
    fontSize: 14,
    fontWeight: 'bold',
    color: theme.text,
    marginBottom: 4,
    textTransform: 'capitalize',
  },
  dateText: {
    fontSize: 11,
    color: theme.textMuted,
    marginBottom: 8,
  },
  authorsRow: {
    marginBottom: 12,
  },
  authorsText: {
    fontSize: 12,
    color: theme.textMuted,
  },
  authorLink: {
    fontSize: 12,
    color: theme.text,
    fontWeight: 'bold',
    textDecorationLine: 'underline',
  },
  authorPlain: {
    fontSize: 12,
    color: theme.textMuted,
  },
  statsRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 10,
    marginBottom: 10,
  },
  statItem: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 2,
  },
  statValue: {
    fontSize: 12,
    fontWeight: 'bold',
    color: theme.text,
  },
  statLabel: {
    fontSize: 12,
    color: theme.textMuted,
  },
  journalPill: {
    flex: 1,
    backgroundColor: theme.surface,
    borderWidth: 1,
    borderColor: theme.border,
    borderRadius: 12,
    paddingHorizontal: 10,
    paddingVertical: 4,
  },
  journalText: {
    fontSize: 12,
    color: theme.text,
    textDecorationLine: 'underline',
  },
  metaRow: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 12,
    marginBottom: 10,
  },
  metaText: {
    fontSize: 11,
    color: theme.textMuted,
  },
  metaLink: {
    fontSize: 11,
    color: theme.textMuted,
    textDecorationLine: 'underline',
  },
  description: {
    fontSize: 12,
    lineHeight: 16,
    color: theme.text,
    marginBottom: 14,
  },
  actionRow: {
    gap: 10,
  },
  actionButton: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 6,
    borderRadius: 10,
    paddingVertical: 12,
  },
  readButton: {
    backgroundColor: theme.text,
  },
  readButtonText: {
    color: theme.surface,
    fontWeight: 'bold',
    fontSize: 14,
  },
  centerContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    padding: 20,
    backgroundColor: theme.background,
  },
  loadingText: {
    marginTop: 10,
    fontSize: 16,
    color: theme.textMuted,
  },
  errorText: {
    fontSize: 16,
    color: theme.danger,
    textAlign: 'center',
  },
  messageText: {
    fontSize: 16,
    color: theme.textMuted,
    textAlign: 'center',
  },
});

export default PaperFeed;
