import { useState, useCallback, useEffect, useRef } from 'react';
import { acsApi } from '@/api/acs';

/**
 * Represents an Azure Communication Services access token.
 */
export interface AcsToken {
  /** The JWT access token string */
  token: string;
  /** ISO timestamp when the token expires */
  expiresOn: string;
  /** User identity information */
  user: {
    /** The ACS communication user ID */
    communicationUserId: string;
  };
}

/**
 * Configuration options for the ACS token hook.
 */
export interface UseAcsTokenOptions {
  /** Unique identifier for the user requesting the token */
  userId: string;
  /** Token scopes to request (default: ['voip']) */
  scopes?: string[];
  /** Whether to automatically refresh the token before expiry (default: true) */
  autoRefresh?: boolean;
  /** Milliseconds before expiry to trigger refresh (default: 5 minutes) */
  refreshBufferMs?: number;
}

/**
 * Return type for the useAcsToken hook.
 */
export interface UseAcsTokenReturn {
  /** The current ACS token, or null if not fetched */
  token: AcsToken | null;
  /** Whether a token fetch is in progress */
  isLoading: boolean;
  /** Error message if token fetch failed */
  error: string | null;
  /** Function to manually fetch a new token */
  fetchToken: () => Promise<AcsToken | null>;
  /** Function to clear the current token */
  clearToken: () => void;
}

/**
 * Hook for managing Azure Communication Services access tokens.
 * 
 * Handles token fetching, automatic refresh before expiry, and cleanup.
 * Tokens are used for video/audio calling with ACS.
 * 
 * @param options - Configuration for token management
 * @returns Object with token state and control functions
 * 
 * @example
 * ```tsx
 * const { token, isLoading, error, fetchToken } = useAcsToken({
 *   userId: user.id,
 *   scopes: ['voip'],
 *   autoRefresh: true,
 * });
 * 
 * useEffect(() => {
 *   fetchToken();
 * }, []);
 * 
 * if (token) {
 *   // Use token for ACS call
 * }
 * ```
 */
export const useAcsToken = ({
  userId,
  scopes = ['voip'],
  autoRefresh = true,
  refreshBufferMs = 5 * 60 * 1000, // 5 minutes before expiry
}: UseAcsTokenOptions): UseAcsTokenReturn => {
  const [token, setToken] = useState<AcsToken | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const refreshTimeoutRef = useRef<NodeJS.Timeout | null>(null);

  /**
   * Clears any scheduled token refresh timeout.
   */
  const clearRefreshTimeout = useCallback((): void => {
    if (refreshTimeoutRef.current) {
      clearTimeout(refreshTimeoutRef.current);
      refreshTimeoutRef.current = null;
    }
  }, []);

  /**
   * Schedules automatic token refresh before expiry.
   * 
   * @param expiresOn - ISO timestamp when the current token expires
   */
  const scheduleRefresh = useCallback((expiresOn: string): void => {
    if (!autoRefresh) return;

    clearRefreshTimeout();

    const expiryTime = new Date(expiresOn).getTime();
    const now = Date.now();
    const refreshTime = expiryTime - refreshBufferMs;
    const delay = Math.max(0, refreshTime - now);

    console.log(`[useAcsToken] Scheduling token refresh in ${Math.round(delay / 1000)}s`);

    refreshTimeoutRef.current = setTimeout(() => {
      console.log('[useAcsToken] Auto-refreshing token...');
      fetchToken();
    }, delay);
  }, [autoRefresh, refreshBufferMs]);

  /**
   * Fetches a new ACS access token from the backend.
   * 
   * @returns The new token on success, or null on failure
   */
  const fetchToken = useCallback(async (): Promise<AcsToken | null> => {
    setIsLoading(true);
    setError(null);

    try {
      console.log(`[useAcsToken] Fetching token for user: ${userId}`);

      const data = await acsApi.getToken(scopes);

      const newToken: AcsToken = {
        token: data.token,
        expiresOn: data.expires_on,
        user: {
          communicationUserId: data.user_id,
        },
      };

      console.log(`[useAcsToken] Token received, expires: ${newToken.expiresOn}`);
      setToken(newToken);
      scheduleRefresh(newToken.expiresOn);

      return newToken;
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Unknown error fetching ACS token';
      console.error('[useAcsToken] Error:', message);
      setError(message);
      return null;
    } finally {
      setIsLoading(false);
    }
  }, [userId, scopes, scheduleRefresh]);

  /**
   * Clears the current token and cancels any scheduled refresh.
   */
  const clearToken = useCallback((): void => {
    clearRefreshTimeout();
    setToken(null);
    setError(null);
  }, [clearRefreshTimeout]);

  /**
   * Checks if the current token is valid and not about to expire.
   * 
   * @returns true if token is valid and has more than refreshBufferMs until expiry
   */
  const isTokenValid = useCallback((): boolean => {
    if (!token) return false;
    const expiryTime = new Date(token.expiresOn).getTime();
    const now = Date.now();
    return expiryTime - now > refreshBufferMs;
  }, [token, refreshBufferMs]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      clearRefreshTimeout();
    };
  }, [clearRefreshTimeout]);

  return {
    token,
    isLoading,
    error,
    fetchToken,
    clearToken,
  };
};
