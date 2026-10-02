// components/PaperFeed.tsx
import * as React from 'react';
import {
  View,
  FlatList,
  ScrollView,
  useWindowDimensions,
  StyleSheet,
  Text,
  ActivityIndicator,
  TouchableOpacity,
  Share,
  RefreshControl,
  StatusBar,
} from 'react-native';
import * as WebBrowser from 'expo-web-browser';
import Animated, {
  useSharedValue,
  useAnimatedStyle,
  withTiming,
  runOnJS,
} from 'react-native-reanimated';
import { Gesture, GestureDetector } from 'react-native-gesture-handler';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { Image } from 'expo-image';
import { useAudioPlayer } from 'expo-audio';
import { useRouter, useFocusEffect } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import * as Haptics from 'expo-haptics';
import { fetchPapers } from '../services/api';
import { useAuth } from '../hooks/useAuth';
import { useFavoritePapers } from '../hooks/useStorage';
import { useBottomTabBarHeight } from 'expo-router/js-tabs';
import { useTheme } from '../hooks/useTheme';
import { useLike } from '../hooks/useLike';
import { useConfirmRead } from '../hooks/useConfirmRead';
import { languageName } from '../constants/languages';
import { playWhenReady } from '../utils/sound';

// The card rests showing only its bottom portion (image visible above it); dragging the handle
// up slides it over most of the screen, covering the image. Only once fully expanded does its
// content become scrollable - while collapsed, dragging elsewhere still pages between papers.
// It stops short of true 0 (see BRAND_BAR_RESERVED_HEIGHT below) so the "PaperBites" brand bar
// stays visible and tappable even when a card is fully expanded.
const COLLAPSED_TOP_RATIO = 0.42;
const ACTION_COLUMN_HEIGHT = 140; // three 40px buttons + gaps
const BRAND_BAR_RESERVED_HEIGHT = 44;

interface Author {
  id: string | null;
  name: string;
}

export interface PaperItem {
  id: string;
  title: string;
  authors: Author[] | null;
  description: string;
  abstract?: string;
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
  trending_category?: string | null;
  like_count?: number;
  read_count?: number;
  is_liked?: boolean;
}

const FeedPaperCard: React.FC<{
  item: PaperItem;
  onExpandedChange: (expanded: boolean) => void;
  isBookmarked: boolean;
  onToggleBookmark: (item: PaperItem) => void;
  headerHeight: number;
}> = ({ item, onExpandedChange, isBookmarked, onToggleBookmark, headerHeight }) => {
  const router = useRouter();
  const { theme } = useTheme();
  const { token } = useAuth();
  // Live window size (not a module-level snapshot) so the layout follows browser resizes and rotation
  const { width, height } = useWindowDimensions();
  const tabBarHeight = useBottomTabBarHeight();
  // Normally 42% down, but never so high that the card covers the action buttons stacked under
  // the header (relevant on short windows) - capped so the card stays usable.
  const COLLAPSED_TOP = Math.min(
    height * 0.75,
    Math.max(height * COLLAPSED_TOP_RATIO, (headerHeight || 70) + ACTION_COLUMN_HEIGHT + 20)
  );
  const styles = React.useMemo(() => createStyles(theme, width, height), [theme, width, height]);
  const { liked, count: likeCount, toggle: toggleLike } = useLike(token, item);
  const confirmRead = useConfirmRead();
  const [justConfirmedRead, setJustConfirmedRead] = React.useState(false);
  const insets = useSafeAreaInsets();
  const BRAND_BAR_TOP_OFFSET = insets.top || StatusBar.currentHeight || 0;
  const BRAND_BAR_BOTTOM_OFFSET = insets.bottom *2 || StatusBar.currentHeight || 0;
  const brandBarTop = BRAND_BAR_TOP_OFFSET + 10;
  // Positions are relative to the card, which is itself shifted down by brandBarTop. Use the real
  // measured header height when we have it - its height differs between platforms (web has no
  // safe-area insets), so the fixed estimate left the controls and badges hidden behind it.
  const controlsTop = headerHeight
    ? headerHeight + 10 - brandBarTop
    : brandBarTop + BRAND_BAR_RESERVED_HEIGHT - 10;
  const expandedTop = headerHeight
    ? headerHeight - brandBarTop
    : brandBarTop + BRAND_BAR_RESERVED_HEIGHT - 10;
  const top = useSharedValue(COLLAPSED_TOP);
  const [isExpanded, setIsExpanded] = React.useState(false);

  // Keep the resting/expanded position correct when the window size or header height changes
  React.useEffect(() => {
    top.value = isExpanded ? expandedTop : COLLAPSED_TOP;
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [height, expandedTop]);

  const setExpanded = React.useCallback(
    (expanded: boolean) => {
      setIsExpanded(expanded);
      onExpandedChange(expanded);
    },
    [onExpandedChange]
  );

  const authors = item.authors || [];

  // "Original" is the raw abstract; "Simpler" is the Gemini rewrite at a lower reading level
  // (paper/summarize.py - genuine simplification, not a condensed summary). Original is the
  // default per-card state. Papers with no abstract at all (rare - only when a source gave us
  // neither an abstract nor enough text to keep one, and description was generated from the PDF
  // full text instead) have nothing to toggle to, so the toggle itself is hidden for those.
  const hasOriginalAbstract = !!item.abstract && item.abstract.trim().length > 0;
  const [descriptionMode, setDescriptionMode] = React.useState<'original' | 'simpler'>('original');
  const displayedDescription =
    descriptionMode === 'original' && hasOriginalAbstract
      ? item.abstract
      : item.description || item.abstract;

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

  const handleShare = async () => {
    try {
      await Share.share({
        message: `${item.title}${item.url ? `\n${item.url}` : ''}`,
        title: item.title,
      });
    } catch (err) {
      console.error('Error sharing paper:', err);
    }
  };

  const handleReadFullText = async () => {
    if (!item.url) return;
    await WebBrowser.openBrowserAsync(item.url);
  };

  const handleConfirmRead = async () => {
    if (!token) {
      router.push('/login');
      return;
    }
    Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Medium).catch(() => {});
    await confirmRead(token, item.id);
    setJustConfirmedRead(true);
  };

  const panGesture = Gesture.Pan()
    .onUpdate((event) => {
      const base = isExpanded ? expandedTop : COLLAPSED_TOP;
      const next = base + event.translationY;
      top.value = Math.min(COLLAPSED_TOP, Math.max(expandedTop, next));
    })
    .onEnd((event) => {
      const shouldExpand = top.value < COLLAPSED_TOP / 2 || event.velocityY < -500;
      const target = shouldExpand ? expandedTop : COLLAPSED_TOP;
      top.value = withTiming(target, { duration: 220 });
      runOnJS(setExpanded)(shouldExpand);
    });

  const animatedCardStyle = useAnimatedStyle(() => ({
    top: top.value,
  }));

  return (
    <View style={[styles.card, { top: brandBarTop }]}>
      <View style={styles.imageContainer}>
        {item.image_url ? (
          <Image source={{ uri: item.image_url }} style={styles.image} contentFit="cover" />
        ) : (
          <View style={[styles.image, styles.imageFallback]} />
        )}
        <View style={[styles.cardActionColumn, { top: controlsTop }]}>
          <TouchableOpacity
            style={styles.cardActionButton}
            onPress={() => {
              Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Light).catch(() => {});
              onToggleBookmark(item);
            }}
          >
            <Ionicons
              name={isBookmarked ? 'bookmark' : 'bookmark-outline'}
              size={20}
              color={isBookmarked ? theme.background : theme.surface}
            />
          </TouchableOpacity>
          <TouchableOpacity
            style={styles.cardActionButton}
            onPress={() => {
              Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Light).catch(() => {});
              toggleLike();
            }}
          >
            <Ionicons
              name={liked ? 'heart' : 'heart-outline'}
              size={20}
              color={liked ? theme.like : theme.surface}
            />
          </TouchableOpacity>
          <TouchableOpacity style={styles.cardActionButton} onPress={handleShare}>
            <Ionicons name="share-outline" size={20} color={theme.surface} />
          </TouchableOpacity>
        </View>
        <View style={[styles.badgeColumn, { top: controlsTop }]}>
          {item.trending_category && (
            <View style={styles.trendingBadge}>
              <Ionicons name="flame" size={12} color={theme.onAccent} />
              <Text style={styles.trendingBadgeText}>Trending in {item.trending_category}</Text>
            </View>
          )}
          {item.categories && item.categories.length > 0 && (
            <View style={styles.categoryBadge}>
              <Text style={styles.categoryBadgeText}>{item.categories[0]}</Text>
            </View>
          )}
          <View style={styles.languageBadge}>
            <Text style={styles.categoryBadgeText}>{languageName(item.language)}</Text>
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
          contentContainerStyle={[styles.infoCardContent, { paddingBottom: 40 + tabBarHeight }]}
          scrollEnabled={isExpanded}
          nestedScrollEnabled
          showsVerticalScrollIndicator={false}
        >
          <Text style={styles.title}>{item.title}</Text>

          {item.published_date && (
            <Text style={styles.dateText}>Published {item.published_date}</Text>
          )}

          <View style={styles.authorsRow}>
            {authors.length === 0 ? (
              <Text style={styles.authorsText}>Unknown authors</Text>
            ) : (
              <Text style={styles.authorsText}>
                {authors.map((author, index) => (
                  <React.Fragment key={`${author.id ?? author.name}-${index}`}>
                    <Text
                      style={author.id ? styles.authorLink : styles.authorPlain}
                      onPress={author.id ? () => goToAuthor(author) : undefined}
                    >
                      {author.name}
                    </Text>
                    {index < authors.length - 1 && <Text style={styles.authorsText}>, </Text>}
                  </React.Fragment>
                ))}
              </Text>
            )}
          </View>

          <View style={styles.statsRow}>
            {item.journal && (
              <TouchableOpacity style={styles.journalPill} onPress={goToJournal}>
                <Text style={styles.journalText}>
                  {item.journal}
                  {item.publication_type ? ` · ${item.publication_type === 'conference' ? 'Conference' : 'Journal'}`+'  ' : ''}
                </Text>
              </TouchableOpacity>
            )}
          </View>

          {item.doi && (
            <View style={styles.metaRow}>
              <Text
                style={styles.statLabel}
              >
                DOI: {item.doi}  
              </Text>
            </View>
          )}

          {hasOriginalAbstract && (
            <View style={styles.descriptionToggle}>
              <TouchableOpacity
                style={[styles.toggleOption, descriptionMode === 'original' && styles.toggleOptionActive]}
                onPress={() => {
                  Haptics.selectionAsync().catch(() => {});
                  setDescriptionMode('original');
                }}
              >
                <Text style={[styles.toggleText, descriptionMode === 'original' && styles.toggleTextActive]}>
                  Original
                </Text>
              </TouchableOpacity>
              <TouchableOpacity
                style={[styles.toggleOption, descriptionMode === 'simpler' && styles.toggleOptionActive]}
                onPress={() => {
                  Haptics.selectionAsync().catch(() => {});
                  setDescriptionMode('simpler');
                }}
              >
                <Text style={[styles.toggleText, descriptionMode === 'simpler' && styles.toggleTextActive]}>
                  Simplified
                </Text>
              </TouchableOpacity>
            </View>
          )}

          <Text style={styles.description}>{displayedDescription}</Text>

          <View style={styles.actionRow}>
            {item.url && (
              <TouchableOpacity
                style={[styles.readButton, styles.actionButton]}
                onPress={handleReadFullText}
              >
                <Text style={styles.readButtonText}>Read Full Text</Text>
                <Ionicons name="open-outline" size={16} color={theme.text} />
              </TouchableOpacity>
            )}
            {!!item.read_count && (
              <View style={styles.readCountPill}>
                <Ionicons name="people" size={14} color={theme.textMuted} />
                <Text style={styles.readCountText}>{item.read_count}</Text>
              </View>
            )}
          </View>

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
      </Animated.View>
    </View>
  );
};

const PAGE_SIZE = 10;
const SWIPE_SOUND = require('../assets/sounds/swipe-whoosh.wav');

type FavoritePapersApi = {
  isFavorite: (paperId: string) => boolean;
  toggleFavorite: (paper: PaperItem) => void;
};

const PaperFeed: React.FC = () => {
  const router = useRouter();
  const { user, token } = useAuth();
  const { theme } = useTheme();
  const { width, height } = useWindowDimensions();
  const styles = React.useMemo(() => createStyles(theme, width, height), [theme, width, height]);
  const [headerHeight, setHeaderHeight] = React.useState(0);
  const insets = useSafeAreaInsets();
  const BRAND_BAR_TOP_OFFSET = insets.top *2 || StatusBar.currentHeight || 0;
  const { isFavorite, toggleFavorite } = useFavoritePapers(token) as unknown as FavoritePapersApi;
  const [papers, setPapers] = React.useState<PaperItem[]>([]);
  const [loading, setLoading] = React.useState(true);
  const [loadingMore, setLoadingMore] = React.useState(false);
  const [refreshing, setRefreshing] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);
  const [anyExpanded, setAnyExpanded] = React.useState(false);
  const [page, setPage] = React.useState(0);
  const [hasMore, setHasMore] = React.useState(true);
  const swipeSound = useAudioPlayer(SWIPE_SOUND);
  const lastPageIndexRef = React.useRef(0);

  // Fetch a page of papers from the backend - passing the token lets the server hard-filter to
  // the signed-in user's chosen interests (see /api/interests), when they've set any.
  const loadPapers = async (reset: boolean) => {
    const pageToLoad = reset ? 0 : page;
    if (!reset && !hasMore) return;
    if (reset) lastPageIndexRef.current = 0;

    try {
      if (reset && papers.length === 0) setLoading(true);
      else if (!reset) setLoadingMore(true);

      const fetched: PaperItem[] = (await fetchPapers({
        token,
        limit: PAGE_SIZE,
        offset: pageToLoad * PAGE_SIZE,
        category: '',
      })) ?? [];

      setHasMore(fetched.length === PAGE_SIZE);
      setPapers((prev) => {
        const combined = reset ? fetched : [...prev, ...fetched];
        // Sort newest to oldest (defensive - the backend already sorts, but this holds
        // regardless of query order).
        return [...combined].sort((a, b) => (b.published_date ?? '').localeCompare(a.published_date ?? ''));
      });
      setPage(pageToLoad + 1);
      setError(null);
    } catch (err) {
      setError('Failed to load papers');
      console.error(err);
    } finally {
      setLoading(false);
      setRefreshing(false);
      setLoadingMore(false);
    }
  };

  // Reload from the top every time Home regains focus (e.g. after logging in elsewhere).
  useFocusEffect(
    React.useCallback(() => {
      loadPapers(true);
    }, [token])
  );

  const handleRefresh = () => {
    setRefreshing(true);
    loadPapers(true);
  };

  const handleEndReached = () => {
    if (!loading && !loadingMore && hasMore) {
      loadPapers(false);
    }
  };

  const playSwipeSound = () => {
    try {
      playWhenReady(swipeSound);
    } catch (err) {
      console.debug('Swipe sound failed to play:', err);
    }
  };

  // Plays the whoosh right as the user releases the swipe, not after the settle animation
  // finishes - waiting for onMomentumScrollEnd made it feel noticeably delayed. iOS hands us
  // targetContentOffset (exactly where the release will land); Android doesn't, so fall back to
  // predicting the next page from the release velocity's direction.
  const handleScrollEndDrag = (event: {
    nativeEvent: {
      contentOffset: { y: number };
      targetContentOffset?: { y: number };
      velocity?: { y: number };
    };
  }) => {
    const { contentOffset, targetContentOffset, velocity } = event.nativeEvent;
    let predictedOffset = contentOffset.y;
    if (targetContentOffset) {
      predictedOffset = targetContentOffset.y;
    } else if (velocity && Math.abs(velocity.y) > 0.3) {
      predictedOffset = contentOffset.y + (velocity.y > 0 ? height : -height);
    }

    const predictedIndex = Math.max(0, Math.round(predictedOffset / height));
    if (predictedIndex !== lastPageIndexRef.current) {
      lastPageIndexRef.current = predictedIndex;
      playSwipeSound();
    }
  };

  // Safety-net resync only (no sound here) - corrects lastPageIndexRef if the release-time
  // prediction above was wrong (e.g. a swipe too weak to actually change pages, which snaps
  // back), so it doesn't drift out of sync with where the feed actually ends up.
  const handleMomentumScrollEnd = (event: { nativeEvent: { contentOffset: { y: number } } }) => {
    lastPageIndexRef.current = Math.round(event.nativeEvent.contentOffset.y / height);
  };

  const handleToggleBookmark = (item: PaperItem) => {
    if (!user) {
      router.push('/login');
      return;
    }
    toggleFavorite(item as any);
  };

  const fixedHeader = (
    <View
      pointerEvents="box-none"
      style={[styles.brandBar]}
      onLayout={(e) => setHeaderHeight(e.nativeEvent.layout.height)}
    >
      <View style={[styles.brandBarSpacer, { paddingTop: BRAND_BAR_TOP_OFFSET }]} pointerEvents="none" />
      <View style={styles.brandBarContent}>
        <Image source={require('../assets/icon.png')} style={styles.brandImage} />
        <Text style={styles.brandText} pointerEvents="none">PaperBites</Text>
        <TouchableOpacity
        style={styles.searchIconButton}
        onPress={() => router.push('/search')}
        hitSlop={10}
      >
        <Ionicons name="search" size={16} color={theme.accent} />
      </TouchableOpacity>
      </View>
      
    </View>
  );

  if (loading) {
    return (
      <View style={styles.flexContainer}>
        {fixedHeader}
        <View style={styles.centerContainer}>
          <ActivityIndicator size="large" color={theme.text} />
          <Text style={styles.loadingText}>Loading papers...</Text>
        </View>
      </View>
    );
  }

  if (error) {
    return (
      <View style={styles.flexContainer}>
        {fixedHeader}
        <View style={styles.centerContainer}>
          <Text style={styles.errorText}>{error}</Text>
        </View>
      </View>
    );
  }

  if (papers.length === 0) {
    return (
      <View style={styles.flexContainer}>
        {fixedHeader}
        <View style={styles.centerContainer}>
          <Text style={styles.messageText}>No papers found</Text>
        </View>
      </View>
    );
  }

  return (
    <View style={styles.flexContainer}>
      <FlatList
        data={papers}
        extraData={headerHeight}
        keyExtractor={(item) => item.id}
        renderItem={({ item }) => (
          <FeedPaperCard
            item={item}
            onExpandedChange={setAnyExpanded}
            isBookmarked={isFavorite(item.id)}
            onToggleBookmark={handleToggleBookmark}
            headerHeight={headerHeight}
          />
        )}
        // Every card is exactly `height` tall - telling FlatList that up front via
        // getItemLayout skips its own (comparatively expensive) dynamic measurement pass, which
        // is what made paging feel janky rather than an instant, deterministic snap to each page.
        getItemLayout={(_, index) => ({ length: height, offset: height * index, index })}
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
        onEndReached={handleEndReached}
        onEndReachedThreshold={0.5}
        onScrollEndDrag={handleScrollEndDrag}
        onMomentumScrollEnd={handleMomentumScrollEnd}
        refreshControl={
          <RefreshControl refreshing={refreshing} onRefresh={handleRefresh} tintColor={theme.text} />
        }
      />
      {fixedHeader}
    </View>
  );
};

const createStyles = (theme: any, width: number, height: number) => StyleSheet.create({
  flexContainer: {
    flex: 1,
  },
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
    backgroundColor: theme.surface,
  },
  brandBar: {
    position: 'absolute',
    top: 0,
    left: 0,
    right: 0,
    flexDirection: 'row',
    alignItems: 'flex-end',
    paddingHorizontal: 16,
    padding: 10,
    backgroundColor: theme.surface,
  },
  brandBarContent: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    gap: 10,
    paddingHorizontal: 16,
    left: -15,
  },
  brandBarSpacer: {
    width: 28,
  },
  brandImage: {
    width: 50,
    height: 50,
    left:-20,
  },
  brandText: {
    flex: 1,
    textAlign: 'center',
    fontFamily: theme.serif,
    fontSize: 18,
    fontWeight: 'bold',
    color: theme.text,
    top: -5,
    left: -15,
    textShadowColor: 'rgba(0, 0, 0, 0.5)',
    textShadowOffset: { width: 0, height: 1 },
    textShadowRadius: 3,
  },
  searchIconButton: {
    width: 32,
    height: 32,
    borderRadius: 16,
    borderColor: theme.border,
    borderWidth: 1,
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: theme.background,
  },
  cardActionColumn: {
    position: 'absolute',
    top: 50,
    left: 16,
    alignItems: 'center',
    gap: 10,
  },
  cardActionButton: {
    width: 40,
    height: 40,
    alignItems: 'center',
    justifyContent: 'center',
    borderRadius: 20,
    backgroundColor: theme.accent,
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
  trendingBadge: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
    backgroundColor: theme.streak,
    paddingHorizontal: 10,
    paddingVertical: 5,
    borderRadius: 16,
  },
  trendingBadgeText: {
    fontSize: 11,
    fontWeight: 'bold',
    color: theme.onAccent,
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
    // Anchored to the screen bottom (rather than a fixed `height` paired with an animated `top`)
    // so its actual height always shrinks to fit between wherever `top` currently is and the
    // bottom of the screen. With a fixed height and `top` allowed to land above 0 (see
    // expandedTop), the card would overflow past the bottom of the screen by that same amount -
    // pushing its own "Read Original Paper" button/footer off-screen and letting the image
    // layer's brand bar peek through underneath.
    bottom: 0,
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
  statLabel: {
    fontSize: 12,
    color: theme.textMuted,
  },
  journalPill: {
    backgroundColor: theme.surface,
    borderWidth: 1,
    borderColor: theme.border,
    borderRadius: 12,
    paddingHorizontal: 10,
    paddingVertical: 4,
    flexShrink: 1,
  },
  journalText: {
    fontSize: 12,
    color: theme.text,
    textDecorationLine: 'underline',
  },
  metaRow: {
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
  descriptionToggle: {
    flexDirection: 'row',
    alignSelf: 'flex-start',
    borderWidth: 1.5,
    borderColor: theme.border,
    borderRadius: 20,
    overflow: 'hidden',
    marginBottom: 10,
  },
  toggleOption: {
    paddingHorizontal: 14,
    paddingVertical: 6,
  },
  toggleOptionActive: {
    backgroundColor: theme.accent,
  },
  toggleText: {
    fontSize: 11,
    color: theme.text,
    fontWeight: 'bold',
  },
  toggleTextActive: {
    color: theme.background,
    fontWeight: '600',
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
    backgroundColor: theme.accent,
  },
  readButtonText: {
    color: theme.text,
    fontWeight: 'bold',
    fontSize: 14,
  },
  readCountPill: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 4,
  },
  readCountText: {
    fontSize: 12,
    color: theme.textMuted,
    fontWeight: '600',
  },
  confirmReadButton: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 6,
    borderRadius: 10,
    borderWidth: 1.5,
    borderColor: theme.border,
    paddingVertical: 10,
    marginTop: 10,
  },
  confirmReadButtonDone: {
    borderColor: theme.accent,
  },
  confirmReadButtonText: {
    color: theme.text,
    fontWeight: '600',
    fontSize: 13,
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
