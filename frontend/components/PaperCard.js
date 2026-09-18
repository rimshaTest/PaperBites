import React from 'react';
import { View, Text, Image, StyleSheet, TouchableOpacity, Dimensions } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import theme from '../constants/theme';

const { width } = Dimensions.get('window');
const CARD_WIDTH = width * 0.9;

const formatAuthors = (authors) => {
  if (!authors || authors.length === 0) return null;
  const names = authors.map((a) => a.name).filter(Boolean);
  if (names.length <= 2) return names.join(', ');
  return `${names[0]}, ${names[1]} +${names.length - 2}`;
};

const formatMeta = (paper) => {
  const parts = [];
  if (paper.journal) parts.push(paper.journal);
  if (paper.published_date) parts.push(paper.published_date);
  return parts.join(' · ');
};

const PaperCard = ({ paper, onPress, isBookmarked = false, onToggleBookmark }) => {
  const authors = formatAuthors(paper.authors);
  const meta = formatMeta(paper);

  return (
    <TouchableOpacity
      style={styles.container}
      activeOpacity={0.8}
      onPress={() => onPress(paper)}
    >
      {paper.image ? (
        <Image source={{ uri: paper.image }} style={styles.thumbnail} resizeMode="cover" />
      ) : null}

      {onToggleBookmark && (
        <TouchableOpacity
          style={[styles.bookmarkButton, !paper.image && styles.bookmarkButtonNoImage]}
          onPress={(e) => {
            e.stopPropagation();
            onToggleBookmark(paper);
          }}
          hitSlop={{ top: 10, bottom: 10, left: 10, right: 10 }}
        >
          <Ionicons
            name={isBookmarked ? 'bookmark' : 'bookmark-outline'}
            size={22}
            color={isBookmarked ? theme.accent : (paper.image ? '#fff' : theme.textMuted)}
          />
        </TouchableOpacity>
      )}

      <View style={styles.infoContainer}>
        <Text style={styles.title} numberOfLines={2}>{paper.title}</Text>
        {authors && <Text style={styles.authors} numberOfLines={1}>{authors}</Text>}
        <Text style={styles.description} numberOfLines={3}>
          {paper.description || paper.abstract}
        </Text>
        {meta ? <Text style={styles.meta}>{meta}</Text> : null}

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

const styles = StyleSheet.create({
  container: {
    width: CARD_WIDTH,
    marginHorizontal: width * 0.05,
    marginVertical: 10,
    borderRadius: 10,
    backgroundColor: theme.surface,
    borderWidth: 1.5,
    borderColor: theme.border,
    overflow: 'hidden',
  },
  thumbnail: {
    width: '100%',
    height: 160,
    backgroundColor: '#f0f0f0',
  },
  bookmarkButton: {
    position: 'absolute',
    top: 10,
    right: 10,
    width: 32,
    height: 32,
    borderRadius: 16,
    backgroundColor: 'rgba(0, 0, 0, 0.4)',
    justifyContent: 'center',
    alignItems: 'center',
  },
  bookmarkButtonNoImage: {
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
    color: theme.textMuted,
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
    color: theme.textMuted,
    marginBottom: 8,
  },
  categoriesContainer: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    marginTop: 2,
  },
  categoryChip: {
    backgroundColor: theme.background,
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
    color: theme.textMuted,
  },
});

export default PaperCard;
