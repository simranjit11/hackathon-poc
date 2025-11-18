import { useState, useCallback } from 'react';
import { setAccessToken, clearAccessToken } from '@/lib/auth';

/**
 * Login request payload
 */
export interface LoginRequest {
  email: string;
  password: string;
  biometricToken?: string;
}

/**
 * Login response
 */
export interface LoginResponse {
  accessToken: string;
  user: {
    id: string;
    email: string;
    roles: string[];
    permissions: string[];
    name?: string;
  };
}

/**
 * Login hook for mobile application
 * 
 * @returns Login function and loading state
 */
export function useLogin() {
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const login = useCallback(async (credentials: LoginRequest): Promise<LoginResponse | null> => {
    setIsLoading(true);
    setError(null);

    try {
      // Get the API endpoint from environment or use default
      const apiEndpoint = process.env.EXPO_PUBLIC_API_ENDPOINT || 'http://localhost:3000';
      const loginUrl = `${apiEndpoint}/api/auth/login`;

      const response = await fetch(loginUrl, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(credentials),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || 'Login failed');
      }

      const data: LoginResponse = await response.json();
      
      // Store access token in AsyncStorage
      await setAccessToken(data.accessToken);

      return data;
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Login failed';
      setError(errorMessage);
      return null;
    } finally {
      setIsLoading(false);
    }
  }, []);

  const logout = useCallback(async () => {
    await clearAccessToken();
    setError(null);
  }, []);

  return {
    login,
    logout,
    isLoading,
    error,
  };
}

