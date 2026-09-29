import { useEffect, useState } from 'react';
import { addLike, removeLike } from '../services/api';

/**
 * Local heart-toggle state for a single paper card, seeded from the paper's own is_liked/
 * like_count (set server-side by api_server.py's _merge_engagement) and optimistically updated
 * on tap - reverted if the request fails.
 */
export function useLike(token, paper) {
  const [liked, setLiked] = useState(!!paper?.is_liked);
  const [count, setCount] = useState(paper?.like_count ?? 0);

  useEffect(() => {
    setLiked(!!paper?.is_liked);
    setCount(paper?.like_count ?? 0);
  }, [paper?.id, paper?.is_liked, paper?.like_count]);

  const toggle = async () => {
    if (!token || !paper) return;
    const next = !liked;
    setLiked(next);
    setCount((c) => Math.max(0, c + (next ? 1 : -1)));
    try {
      const result = next ? await addLike(token, paper.id) : await removeLike(token, paper.id);
      if (result) {
        setLiked(result.liked);
        setCount(result.like_count);
      }
    } catch (err) {
      console.error('Error toggling like:', err);
      setLiked(!next);
      setCount((c) => Math.max(0, c + (next ? -1 : 1)));
    }
  };

  return { liked, count, toggle };
}
