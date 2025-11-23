import { useCallback, useState } from 'react';
import { setAccessToken } from '@/lib/auth';

/**
 * Signup request
 */
export interface SignupRequest {
  email: string;
  password: string;
  name?: string;
}

/**
 * Signup response
 */
export interface SignupResponse {
  accessToken: string;
  user: {
    id: string;
    email: string;
    name?: string;
    roles: string[];
    permissions: string[];
  };
}

/**
 * Signup hook for web application
 *
 * @returns Signup function and loading state
 */
export function useSignup() {
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const signup = useCallback(async (data: SignupRequest): Promise<SignupResponse | null> => {
    setIsLoading(true);
    setError(null);

    try {
      const response = await fetch('/api/auth/signup', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(data),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || 'Signup failed');
      }

      const result: SignupResponse = await response.json();

      // Store access token
      setAccessToken(result.accessToken);

      return result;
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Signup failed';
      setError(errorMessage);
      return null;
    } finally {
      setIsLoading(false);
    }
  }, []);

  return {
    signup,
    isLoading,
    error,
  };
}
