/**
 * frontend/src/context/AuthContext.jsx
 * Owner: Person 2 | Week: 6
 * 
 * Clean, stable Authentication Context without re-render loops or auth storms.
 * Manages JWT session tokens, user profiles, RBAC permissions, and login modal state.
 */

import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { loginUser, getCurrentUser } from '../api/incidents';

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const queryClient = useQueryClient();
  const [token, setToken] = useState(() => localStorage.getItem('synapse_access_token') || null);
  const [user, setUser] = useState(() => {
    try {
      const saved = localStorage.getItem('synapse_user');
      return saved ? JSON.parse(saved) : null;
    } catch {
      return null;
    }
  });
  const [isLoading, setIsLoading] = useState(true);
  const [isAuthModalOpen, setIsAuthModalOpen] = useState(false);

  // Clean login function
  const login = useCallback(async (username, password) => {
    // 1. Authenticate credentials against /api/auth/login
    const data = await loginUser(username, password);
    const accessToken = data.access_token;
    if (!accessToken) {
      throw new Error('Authentication succeeded but no access token was returned.');
    }

    // 2. Persist access token immediately
    localStorage.setItem('synapse_access_token', accessToken);
    setToken(accessToken);

    // 3. Fetch full user profile with the newly acquired token
    let activeProfile = null;
    try {
      activeProfile = await getCurrentUser();
      localStorage.setItem('synapse_user', JSON.stringify(activeProfile));
      setUser(activeProfile);
    } catch (profileErr) {
      // Fallback user object if /api/auth/me has a delay
      activeProfile = {
        username,
        role: data.role || (username === 'admin' ? 'ADMIN' : username === 'sre_lead' ? 'SRE' : 'VIEWER'),
      };
      localStorage.setItem('synapse_user', JSON.stringify(activeProfile));
      setUser(activeProfile);
    }

    // 4. Invalidate all cached queries so dashboard populates immediately
    queryClient.invalidateQueries();

    // 5. Close login modal
    setIsAuthModalOpen(false);
    return activeProfile;
  }, [queryClient]);

  const logout = useCallback(() => {
    localStorage.removeItem('synapse_access_token');
    localStorage.removeItem('synapse_user');
    setToken(null);
    setUser(null);
    queryClient.clear();
  }, [queryClient]);

  // Single one-time mount effect: verify existing token or settle initial state
  useEffect(() => {
    let isMounted = true;

    async function initAuth() {
      const savedToken = localStorage.getItem('synapse_access_token');
      if (!savedToken) {
        if (isMounted) setIsLoading(false);
        return;
      }

      try {
        const profile = await getCurrentUser();
        if (isMounted) {
          setUser(profile);
          localStorage.setItem('synapse_user', JSON.stringify(profile));
        }
      } catch (err) {
        console.warn('Stored token is invalid or expired:', err.message);
        if (isMounted) {
          logout();
        }
      } finally {
        if (isMounted) {
          setIsLoading(false);
        }
      }
    }

    initAuth();

    const handleUnauthorized = () => {
      logout();
    };
    window.addEventListener('synapse:unauthorized', handleUnauthorized);

    return () => {
      isMounted = false;
      window.removeEventListener('synapse:unauthorized', handleUnauthorized);
    };
  }, [logout]);

  const role = user?.role?.toUpperCase() || 'VIEWER';
  const isAdmin = role === 'ADMIN';
  const isSRE = role === 'SRE';
  const canRemediate = role === 'ADMIN' || role === 'SRE';

  const value = {
    user,
    token,
    role,
    isAuthenticated: !!token && !!user,
    isAdmin,
    isSRE,
    canRemediate,
    isLoading,
    isAuthModalOpen,
    openAuthModal: () => setIsAuthModalOpen(true),
    closeAuthModal: () => setIsAuthModalOpen(false),
    login,
    logout,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}
