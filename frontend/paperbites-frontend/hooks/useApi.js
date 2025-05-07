import { useState, useEffect, useCallback } from 'react';
import ApiConfig from '../constants/ApiConfig';

/**
 * Custom hook for fetching data from the API
 * 
 * @param {string} endpoint - API endpoint to fetch
 * @param {Object} options - Options for the fetch request
 * @param {Object} queryParams - Query parameters for the URL
 * @param {boolean} fetchOnMount - Whether to fetch data on component mount
 * @returns {Object} - Fetch state and refetch function
 */
export const useApi = (
  endpoint, 
  options = {}, 
  queryParams = {}, 
  fetchOnMount = true
) => {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const fetchData = useCallback(async (customParams = {}) => {
    setLoading(true);
    setError(null);

    try {
      // Build URL with query parameters
      const url = ApiConfig.buildUrl(endpoint, { ...queryParams, ...customParams });
      
      // Merge default options with provided options
      const fetchOptions = {
        ...ApiConfig.defaultOptions,
        ...options
      };

      // Make the request
      const response = await fetch(url, fetchOptions);

      // Check if response is ok
      if (!response.ok) {
        throw new Error(`HTTP error! Status: ${response.status}`);
      }

      // Parse response
      const result = await response.json();
      setData(result);
      return result;
    } catch (err) {
      const errorMessage = ApiConfig.handleApiError(err);
      setError(errorMessage);
      return null;
    } finally {
      setLoading(false);
    }
  }, [endpoint, options, queryParams]);

  // Fetch data on mount if enabled
  useEffect(() => {
    if (fetchOnMount) {
      fetchData();
    }
  }, [fetchData, fetchOnMount]);

  return { data, loading, error, refetch: fetchData };
};

/**
 * Custom hook for fetching all videos with pagination
 * 
 * @param {Object} options - Initial fetch options
 * @returns {Object} - Videos data, loading state, and functions
 */
export const useVideos = (options = {}) => {
  const [videos, setVideos] = useState([]);
  const [page, setPage] = useState(0);
  const [hasMore, setHasMore] = useState(true);
  const pageSize = options.limit || ApiConfig.PAGE_SIZE;

  const { loading, error, refetch } = useApi(
    ApiConfig.ENDPOINTS.VIDEOS,
    {},
    { ...options, limit: pageSize, offset: 0 },
    false // Don't fetch on mount
  );

  // Load initial page
  const loadInitial = useCallback(async () => {
    setPage(0);
    setHasMore(true);
    
    const result = await refetch({ offset: 0 });
    
    if (result) {
      setVideos(result);
      setHasMore(result.length >= pageSize);
    }
  }, [refetch, pageSize]);

  // Load more videos (next page)
  const loadMore = useCallback(async () => {
    if (loading || !hasMore) return;
    
    const nextPage = page + 1;
    const offset = nextPage * pageSize;
    
    const result = await refetch({ offset });
    
    if (result) {
      setVideos(prevVideos => [...prevVideos, ...result]);
      setHasMore(result.length >= pageSize);
      setPage(nextPage);
    }
  }, [loading, hasMore, page, pageSize, refetch]);

  // Refresh videos
  const refresh = useCallback(async () => {
    return loadInitial();
  }, [loadInitial]);

  return {
    videos,
    loading,
    error,
    hasMore,
    loadInitial,
    loadMore,
    refresh
  };
};

/**
 * Custom hook for fetching a single video by ID
 * 
 * @param {string} id - Video ID
 * @param {boolean} fetchOnMount - Whether to fetch on component mount
 * @returns {Object} - Video data, loading state, and refetch function
 */
export const useVideo = (id, fetchOnMount = true) => {
  return useApi(
    ApiConfig.ENDPOINTS.VIDEO_DETAIL(id),
    {},
    {},
    fetchOnMount
  );
};

/**
 * Custom hook for fetching topics
 * 
 * @param {boolean} fetchOnMount - Whether to fetch on component mount
 * @returns {Object} - Topics data, loading state, and refetch function
 */
export const useTopics = (fetchOnMount = true) => {
  return useApi(
    ApiConfig.ENDPOINTS.TOPICS,
    {},
    {},
    fetchOnMount
  );
};