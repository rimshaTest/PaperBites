import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import * as authApi from '../services/auth';
import { getAuthSession, saveAuthSession, clearAuthSession } from '../services/storage';

const AuthContext = createContext(null);

/**
 * Holds the current account session for the whole app.
 *
 * Persists the session token + user locally, but treats the server as the
 * source of truth: on mount it re-validates the token via GET /api/auth/me
 * and clears the stored session if it's no longer valid (expired, or the
 * server was reset), so the UI never gets stuck thinking it's logged in.
 *
 * This lives in a context (rather than being a plain hook each screen calls
 * independently) so that logging in on one screen is immediately visible to
 * every other already-mounted screen in the stack - e.g. going "back" from
 * /login to Home should show the bookmark as toggleable right away.
 */
export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [token, setToken] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    let cancelled = false;

    const restore = async () => {
      try {
        const session = await getAuthSession();
        if (!session.token) return;

        const { user: freshUser } = await authApi.getMe(session.token);
        if (cancelled) return;
        setToken(session.token);
        setUser(freshUser);
      } catch (err) {
        await clearAuthSession();
      } finally {
        if (!cancelled) setLoading(false);
      }
    };

    restore();
    return () => { cancelled = true; };
  }, []);

  const signup = useCallback(async (email, password) => {
    setError(null);
    try {
      const { token: newToken, user: newUser } = await authApi.signup(email, password);
      await saveAuthSession(newToken, newUser);
      setToken(newToken);
      setUser(newUser);
      return true;
    } catch (err) {
      setError(err.message);
      return false;
    }
  }, []);

  const login = useCallback(async (email, password) => {
    setError(null);
    try {
      const { token: newToken, user: newUser } = await authApi.login(email, password);
      await saveAuthSession(newToken, newUser);
      setToken(newToken);
      setUser(newUser);
      return true;
    } catch (err) {
      setError(err.message);
      return false;
    }
  }, []);

  const logout = useCallback(async () => {
    if (token) {
      await authApi.logout(token).catch(() => {});
    }
    await clearAuthSession();
    setToken(null);
    setUser(null);
  }, [token]);

  return (
    <AuthContext.Provider value={{ user, token, loading, error, signup, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
};

/**
 * Access the current account session. Must be used within <AuthProvider>.
 */
export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};
