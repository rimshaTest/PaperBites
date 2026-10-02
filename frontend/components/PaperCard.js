import React, { useMemo } from 'react';
import { View, Text, Image, StyleSheet, TouchableOpacity, Share } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { useTheme } from '../hooks/useTheme';
import { useAuth } from '../hooks/useAuth';
import { useLike } from '../hooks/useLike';

const PaperCard = ({ paper, onPress, isBookmarked = false, onToggleBookmark, onAuthorPress, onJournalPress }) => {
  const { theme } = useTheme();
  const { token } = useAuth();
  const styles = useMemo(() => createStyles(theme), [theme]);
  const { liked, toggle: toggleLike } = useLike(token, paper);
  const authors = paper.authors || [];
  const visibleAuthors = authors.slice(0, 2);
  const extraCount = authors.length - visibleAuthors.length;

  const handleShare = async (e) => {
    e.stopPropagation();
    try {
      await Share.share({
        message: `${paper.title}${paper.url ? `\n${paper.url}` : ''}`,
        title: paper.title,
      });
    } catch (err) {
      console.error('Error sharing paper:', err);
    }
  };

  return (
    <TouchableOpacity
      style={styles.container}
      activeOpacity={0.8}
      onPress={() => onPress(paper)}
    >
      {paper.image_url ? (
        <Image source={{ uri: paper.image_url }} style={styles.thumbnail} resizeMode="cover" />
      ) : null}

      <View style={styles.cardActionRow}>
        <TouchableOpacity
          style={[styles.cardIconButton, !paper.image_url && styles.cardIconButtonNoImage]}
          onPress={(e) => {
            e.stopPropagation();
            toggleLike();
          }}
          hitSlop={{ top: 10, bottom: 10, left: 10, right: 10 }}
        >
          <Ionicons
            name={liked ? 'heart' : 'heart-outline'}
            size={20}
            color={liked ? theme.like : (paper.image_url ? theme.onAccent : theme.textMuted)}
          />
        </TouchableOpacity>

        <TouchableOpacity
          style={[styles.cardIconButton, !paper.image_url && styles.cardIconButtonNoImage]}
          onPress={handleShare}
          hitSlop={{ top: 10, bottom: 10, left: 10, right: 10 }}
        >
          <Ionicons
            name="share-outline"
            size={20}
            color={paper.image_url ? theme.onAccent : theme.textMuted}
          />
        </TouchableOpacity>

        {onToggleBookmark && (
          <TouchableOpacity
            style={[styles.cardIconButton, !paper.image_url && styles.cardIconButtonNoImage]}
            onPress={(e) => {
              e.stopPropagation();
              onToggleBookmark(paper);
            }}
            hitSlop={{ top: 10, bottom: 10, left: 10, right: 10 }}
          >
            <Ionicons
              name={isBookmarked ? 'bookmark' : 'bookmark-outline'}
              size={22}
              color={isBookmarked ? theme.accent : (paper.image_url ? theme.onAccent : theme.textMuted)}
            />
          </TouchableOpacity>
        )}
      </View>

      <View style={styles.infoContainer}>
        <Text style={styles.title} numberOfLines={2}>{paper.title}</Text>

        {visibleAuthors.length > 0 && (
          <Text style={styles.authors} numberOfLines={1}>
            {visibleAuthors.map((author, index) => (
              <Text
                key={author.id || author.name}
                onPress={author.id && onAuthorPress ? (e) => { e.stopPropagation(); onAuthorPress(author); } : undefined}
                style={author.id && onAuthorPress ? styles.link : undefined}
              >
                {author.name}{index < visibleAuthors.length - 1 ? ', ' : ''}
              </Text>
            ))}
            {extraCount > 0 ? ` +${extraCount}` : ''}
          </Text>
        )}

        <Text style={styles.description} numberOfLines={3}>
          {paper.description || paper.abstract}
        </Text>

        {(paper.journal || paper.published_date) && (
          <Text style={styles.meta}>
            {paper.journal ? (
              <Text
                onPress={onJournalPress ? (e) => { e.stopPropagation(); onJournalPress(paper.journal); } : undefined}
                style={onJournalPress ? styles.link : undefined}
              >
                {paper.journal}
              </Text>
            ) : null}
            {paper.journal && paper.published_date ? ' · ' : ''}
            {paper.published_date || ''}
          </Text>
        )}

        {paper.categories && paper.categories.length > 0 && (
          <View style={styles.categoriesContainer}>
            {paper.categories.slice(0, 3).map((category, index) => (
              <View key={index} style={styles.categoryChip}>
                <Text style={styles.categoryText}>{category}</Text>
              </View>
            ))}
          </View>
        )}
      </View>
    </TouchableOpacity>
  );
};

const createStyles = (theme) => StyleSheet.create({
  container: {
    // Fills whatever space its parent gives it (full row on phones, one column of the grid on
    // wide screens) instead of a width computed once from the window at load time.
    flex: 1,
    marginHorizontal: 16,
    marginVertical: 10,
    borderRadius: 10,
    backgroundColor: theme.accent,
    borderWidth: 1.5,
    borderColor: theme.border,
    overflow: 'hidden',
  },
  thumbnail: {
    width: '100%',
    height: 160,
    backgroundColor: theme.surface,
  },
  cardActionRow: {
    position: 'absolute',
    top: 10,
    right: 10,
    flexDirection: 'row',
    gap: 6,
  },
  cardIconButton: {
    width: 32,
    height: 32,
    borderRadius: 16,
    backgroundColor: theme.background,
    justifyContent: 'center',
    alignItems: 'center',
  },
  cardIconButtonNoImage: {
    backgroundColor: 'transparent',
  },
  infoContainer: {
    padding: 14,
  },
  title: {
    fontFamily: theme.serif,
    fontSize: 17,
    fontWeight: 'bold',
    marginBottom: 4,
    color: theme.text,
  },
  authors: {
    fontSize: 13,
    color: theme.text,
    marginBottom: 6,
  },
  description: {
    fontSize: 14,
    color: theme.text,
    lineHeight: 19,
    marginBottom: 8,
  },
  meta: {
    fontSize: 12,
    color: theme.text,
    marginBottom: 8,
  },
  link: {
    color: theme.text,
    textDecorationLine: 'underline',
  },
  categoriesContainer: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    marginTop: 2,
  },
  categoryChip: {
    backgroundColor: theme.surface,
    borderWidth: 1,
    borderColor: theme.border,
    paddingHorizontal: 8,
    paddingVertical: 4,
    borderRadius: 16,
    marginRight: 6,
    marginBottom: 6,
  },
  categoryText: {
    fontSize: 12,
    lineHeight: 16,
    color: theme.text,
  },
});

export default PaperCard;
