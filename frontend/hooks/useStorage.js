import { useState, useEffect, useCallback } from 'react';
import { fetchBookmarks, addBookmark, removeBookmark } from '../services/api';

/**
 * Custom hook for managing bookmarked ("favorite") papers.
 *
 * Bookmarks are stored server-side (see backend/bookmarks.py) and scoped to
 * the signed-in account, so a session token (from useAuth()) is required.
 * With no token, this hook simply reports an empty, non-loading list rather
 * than calling the API - callers should route to /login if they want to let
 * a signed-out user bookmark something.
 *
 * @param {string|null} token - Session token from useAuth()
 * @returns {Object} - Favorite papers data and functions
 */
export const useFavoritePapers = (token) => {
  const [favorites, setFavorites] = useState([]);
  const [loading, setLoading] = useState(!!token);
  const [error, setError] = useState(null);

  // (Re)load bookmarks whenever the session token changes (login/logout)
  useEffect(() => {
    let cancelled = false;

    if (!token) {
      setFavorites([]);
      setLoading(false);
      return;
    }

    const load = async () => {
      try {
        setLoading(true);
        const bookmarked = await fetchBookmarks(token);
        if (!cancelled) setFavorites(bookmarked);
      } catch (err) {
        console.error('Error loading favorites:', err);
        if (!cancelled) setError('Failed to load favorite papers');
      } finally {
        if (!cancelled) setLoading(false);
      }
    };

    load();
    return () => { cancelled = true; };
  }, [token]);

  // Check if a paper is in favorites
  const isFavorite = useCallback((paperId) => {
    return favorites.some(paper => paper.id === paperId);
  }, [favorites]);

  // Add a paper to favorites
  const addFavorite = useCallback(async (paper) => {
    if (!paper || !paper.id || !token) return false;
    if (isFavorite(paper.id)) return true;

    // Optimistic update so the UI reacts immediately
    setFavorites(prev => [paper, ...prev]);

    try {
      await addBookmark(token, paper.id);
      return true;
    } catch (err) {
      console.error('Error adding favorite:', err);
      // Roll back on failure
      setFavorites(prev => prev.filter(p => p.id !== paper.id));
      return false;
    }
  }, [token, isFavorite]);

  // Remove a paper from favorites
  const removeFavorite = useCallback(async (paperId) => {
    if (!token) return false;

    const previous = favorites;
    setFavorites(prev => prev.filter(paper => paper.id !== paperId));

    try {
      await removeBookmark(token, paperId);
      return true;
    } catch (err) {
      console.error('Error removing favorite:', err);
      // Roll back on failure
      setFavorites(previous);
      return false;
    }
  }, [token, favorites]);

  // Toggle favorite status
  const toggleFavorite = useCallback(async (paper) => {
    if (isFavorite(paper.id)) {
      return removeFavorite(paper.id);
    } else {
      return addFavorite(paper);
    }
  }, [isFavorite, removeFavorite, addFavorite]);

  return {
    favorites,
    loading,
    error,
    isFavorite,
    addFavorite,
    removeFavorite,
    toggleFavorite,
  };
};
