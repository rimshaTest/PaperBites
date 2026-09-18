import { API_BASE_URL } from './api';

const parseOrThrow = async (response) => {
  const body = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(body.detail || `API error: ${response.status}`);
  }
  return body;
};

/**
 * Create a new account.
 * @returns {Promise<{token: string, user: {id: string, email: string}}>}
 */
export const signup = async (email, password) => {
  const response = await fetch(`${API_BASE_URL}/auth/signup`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, password }),
  });
  return parseOrThrow(response);
};

/**
 * Log in to an existing account.
 * @returns {Promise<{token: string, user: {id: string, email: string}}>}
 */
export const login = async (email, password) => {
  const response = await fetch(`${API_BASE_URL}/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, password }),
  });
  return parseOrThrow(response);
};

/**
 * Invalidate a session token server-side.
 */
export const logout = async (token) => {
  await fetch(`${API_BASE_URL}/auth/logout`, {
    method: 'POST',
    headers: { Authorization: `Bearer ${token}` },
  });
};

/**
 * Look up the account a session token belongs to. Throws if the token is
 * missing or no longer valid (expired, or logged out elsewhere).
 * @returns {Promise<{user: {id: string, email: string}}>}
 */
export const getMe = async (token) => {
  const response = await fetch(`${API_BASE_URL}/auth/me`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  return parseOrThrow(response);
};
