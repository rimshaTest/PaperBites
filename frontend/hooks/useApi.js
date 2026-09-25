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
