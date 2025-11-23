import { useCallback, useState } from 'react';
import { clearAccessToken, setAccessToken } from '@/lib/auth';

/**
 * Login request payload
 */
export interface LoginRequest {
  email: string;
  password: string;
  biometricToken?: string;
  otpCode?: string;
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
 * Login hook for web application
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
      const response = await fetch('/api/auth/login', {
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

      // Store access token
      setAccessToken(data.accessToken);

      return data;
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Login failed';
      setError(errorMessage);
      return null;
    } finally {
      setIsLoading(false);
    }
  }, []);

  const logout = useCallback(() => {
    clearAccessToken();
    setError(null);
  }, []);

  return {
    login,
    logout,
    isLoading,
    error,
  };
}
