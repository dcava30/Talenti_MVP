import { useState, useCallback, useEffect, useRef } from 'react';
import { acsApi } from '@/api/acs';
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
export const useAcsToken = ({ userId, scopes = ['voip'], autoRefresh = true, refreshBufferMs = 5 * 60 * 1000, // 5 minutes before expiry
 }) => {
    const [token, setToken] = useState(null);
    const [isLoading, setIsLoading] = useState(false);
    const [error, setError] = useState(null);
    const refreshTimeoutRef = useRef(null);
    /**
     * Clears any scheduled token refresh timeout.
     */
    const clearRefreshTimeout = useCallback(() => {
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
    const scheduleRefresh = useCallback((expiresOn) => {
        if (!autoRefresh)
            return;
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
    const fetchToken = useCallback(async () => {
        setIsLoading(true);
        setError(null);
        try {
            console.log(`[useAcsToken] Fetching token for user: ${userId}`);
            const data = await acsApi.getToken(scopes);
            const newToken = {
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
        }
        catch (err) {
            const message = err instanceof Error ? err.message : 'Unknown error fetching ACS token';
            console.error('[useAcsToken] Error:', message);
            setError(message);
            return null;
        }
        finally {
            setIsLoading(false);
        }
    }, [userId, scopes, scheduleRefresh]);
    /**
     * Clears the current token and cancels any scheduled refresh.
     */
    const clearToken = useCallback(() => {
        clearRefreshTimeout();
        setToken(null);
        setError(null);
    }, [clearRefreshTimeout]);
    /**
     * Checks if the current token is valid and not about to expire.
     *
     * @returns true if token is valid and has more than refreshBufferMs until expiry
     */
    const isTokenValid = useCallback(() => {
        if (!token)
            return false;
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
