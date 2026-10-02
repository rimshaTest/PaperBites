import React from 'react';
import {
  View,
  Text,
  FlatList,
  StyleSheet,
  TouchableOpacity,
  Platform,
  useWindowDimensions,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useRouter, useFocusEffect } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import PaperCard from '../../components/PaperCard';
import { useFavoritePapers } from '../../hooks/useStorage';
import { useAuth } from '../../hooks/useAuth';
import { useBottomTabBarHeight } from 'expo-router/js-tabs';
import { useTheme } from '../../hooks/useTheme';

export default function SavedScreen() {
  const router = useRouter();
  const { user, token, loading: authLoading } = useAuth();
  const { theme } = useTheme();
  const { width } = useWindowDimensions();
  const tabBarHeight = useBottomTabBarHeight();
  // Two columns on wide screens; on phones, one
  const numColumns = width >= 900 ? 2 : 1;
  // Leave room for the raised center button; on iOS the tab bar floats over content too
  const bottomPadding = 48 + (Platform.OS === 'ios' ? tabBarHeight : 0);
  const styles = React.useMemo(() => createStyles(theme), [theme]);
  const { favorites, loading, isFavorite, removeFavorite, refetch } = useFavoritePapers(token);

  // Reload whenever the Saved tab regains focus, so bookmarks added/removed
  // elsewhere (e.g. from the Home feed) don't leave this list stale.
  useFocusEffect(
    React.useCallback(() => {
      refetch();
    }, [refetch])
  );

  const handlePaperPress = (paper) => {
    router.push(`/paper/${paper.id}`);
  };

  const handleAuthorPress = (author) => {
    router.push(`/author/${encodeURIComponent(author.id)}`);
  };

  const handleJournalPress = (journal) => {
    router.push(`/journal/${encodeURIComponent(journal)}`);
  };

  return (
    <SafeAreaView style={styles.container}>
      <View style={styles.header}>
        <View style={styles.headerLeft}>
          <Text style={styles.headerTitle}>Saved</Text>
        </View>
      </View>

      {authLoading || loading ? (
        <View style={styles.centerContainer}>
          <Text style={styles.emptyText}>Loading saved papers...</Text>
        </View>
      ) : !user ? (
        <View style={styles.centerContainer}>
          <Ionicons name="lock-closed-outline" size={40} color={theme.textMuted} />
          <Text style={styles.emptyText}>Log in to see your saved papers.</Text>
          <TouchableOpacity style={styles.loginButton} onPress={() => router.push('/login')}>
            <Text style={styles.loginButtonText}>Log In</Text>
          </TouchableOpacity>
        </View>
      ) : favorites.length === 0 ? (
        <View style={styles.centerContainer}>
          <Ionicons name="bookmark-outline" size={40} color={theme.textMuted} />
          <Text style={styles.emptyText}>
            Nothing saved yet. Tap the bookmark icon on any paper to keep it here.
          </Text>
        </View>
      ) : (
        <FlatList
          key={numColumns}
          numColumns={numColumns}
          data={favorites}
          renderItem={({ item }) => (
            <View style={styles.gridCell}>
            <PaperCard
              paper={item}
              onPress={handlePaperPress}
              isBookmarked={isFavorite(item.id)}
              onToggleBookmark={() => removeFavorite(item.id)}
              onAuthorPress={handleAuthorPress}
              onJournalPress={handleJournalPress}
            />
            </View>
          )}
          keyExtractor={(item) => item.id}
          showsVerticalScrollIndicator={false}
          contentContainerStyle={[styles.papersList, { paddingBottom: bottomPadding }]}
        />
      )}
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
    paddingHorizontal: 20,
    paddingVertical: 16,
    borderBottomWidth: 1.5,
    borderBottomColor: theme.border,
    backgroundColor: theme.surface,
  },
  headerLeft: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
  },
  headerTitle: {
    fontFamily: theme.serif,
    fontSize: 22,
    fontWeight: 'bold',
    color: theme.text,
  },
  centerContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    padding: 30,
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
  papersList: {
    paddingTop: 10,
  },
  gridCell: {
    flex: 1,
  },
});
