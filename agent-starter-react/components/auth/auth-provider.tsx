'use client';

import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import { getAccessToken, clearAccessToken } from '@/lib/auth';
import { useLogin } from '@/hooks/useLogin';
import { useSignup } from '@/hooks/useSignup';

interface User {
  id: string;
  email: string;
  name?: string;
  roles: string[];
  permissions: string[];
}

interface AuthContextType {
  user: User | null;
  isLoading: boolean;
  isAuthenticated: boolean;
  login: (email: string, password: string) => Promise<boolean>;
  signup: (email: string, password: string, name?: string) => Promise<boolean>;
  logout: () => void;
  checkAuth: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const router = useRouter();
  const { login: loginHook } = useLogin();
  const { signup: signupHook } = useSignup();

  const checkAuth = useCallback(async () => {
    const token = getAccessToken();
    if (!token) {
      setIsLoading(false);
      return;
    }

    try {
      const response = await fetch('/api/auth/me', {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });

      if (response.ok) {
        const userData = await response.json();
        setUser(userData.user);
      } else {
        clearAccessToken();
        setUser(null);
      }
    } catch (error) {
      console.error('Auth check failed:', error);
      clearAccessToken();
      setUser(null);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    checkAuth();
  }, [checkAuth]);

  const login = useCallback(async (email: string, password: string): Promise<boolean> => {
    const result = await loginHook({ email, password });
    if (result) {
      setUser(result.user);
      router.push('/');
      return true;
    }
    return false;
  }, [loginHook, router]);

  const signup = useCallback(async (email: string, password: string, name?: string): Promise<boolean> => {
    const result = await signupHook({ email, password, name });
    if (result) {
      setUser(result.user);
      router.push('/');
      return true;
    }
    return false;
  }, [signupHook, router]);

  const logout = useCallback(async () => {
    const token = getAccessToken();
    if (token) {
      try {
        await fetch('/api/auth/logout', {
          method: 'POST',
          headers: {
            Authorization: `Bearer ${token}`,
          },
        });
      } catch (error) {
        console.error('Logout API call failed:', error);
      }
    }
    clearAccessToken();
    setUser(null);
    router.push('/login');
  }, [router]);

  return (
    <AuthContext.Provider
      value={{
        user,
        isLoading,
        isAuthenticated: !!user,
        login,
        signup,
        logout,
        checkAuth,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}

