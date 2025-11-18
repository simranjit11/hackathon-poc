/**
 * Web 2FA Authentication Hook
 * 
 * Provides two-factor authentication functionality for web users
 * Supports SMS and Email OTP verification
 */

import { useState, useCallback } from 'react';

export type TwoFactorMethod = 'sms' | 'email';

export interface TwoFactorAuthResult {
  success: boolean;
  error?: string;
  sessionId?: string;
}

export interface Use2FAReturn {
  sendOTP: (method: TwoFactorMethod, phoneOrEmail: string) => Promise<{ success: boolean; error?: string; sessionId?: string }>;
  verifyOTP: (code: string, sessionId?: string) => Promise<TwoFactorAuthResult>;
  isLoading: boolean;
  isOTPSent: boolean;
}

/**
 * Hook for two-factor authentication
 * 
 * @returns 2FA functions and state
 */
export function use2FA(): Use2FAReturn {
  const [isLoading, setIsLoading] = useState(false);
  const [isOTPSent, setIsOTPSent] = useState(false);
  const [sessionId, setSessionId] = useState<string | null>(null);

  /**
   * Send OTP to user's phone or email
   * 
   * @param method - 'sms' or 'email'
   * @param phoneOrEmail - Phone number or email address
   * @returns Success status and optional error message
   */
  const sendOTP = useCallback(
    async (method: TwoFactorMethod, phoneOrEmail: string): Promise<{ success: boolean; error?: string; sessionId?: string }> => {
      setIsLoading(true);
      try {
        const response = await fetch('/api/auth/2fa/send', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            method,
            phoneOrEmail,
          }),
        });

        if (!response.ok) {
          const errorData = await response.json();
          return {
            success: false,
            error: errorData.error || 'Failed to send OTP',
          };
        }

        const data = await response.json();
        setSessionId(data.sessionId);
        setIsOTPSent(true);
        return { success: true, sessionId: data.sessionId };
      } catch (error) {
        console.error('Error sending OTP:', error);
        return {
          success: false,
          error: error instanceof Error ? error.message : 'Unknown error',
        };
      } finally {
        setIsLoading(false);
      }
    },
    []
  );

  /**
   * Verify OTP code
   * 
   * @param code - The OTP code entered by the user
   * @param sessionId - The session ID from sendOTP response
   * @returns Authentication result with success status
   */
  const verifyOTP = useCallback(
    async (code: string, sessionIdParam?: string): Promise<TwoFactorAuthResult> => {
      setIsLoading(true);
      const currentSessionId = sessionIdParam || sessionId;
      
      if (!currentSessionId) {
        return {
          success: false,
          error: 'No active 2FA session. Please request a new OTP.',
        };
      }

      try {
        const response = await fetch('/api/auth/2fa/verify', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            code,
            sessionId: currentSessionId,
          }),
        });

        if (!response.ok) {
          const errorData = await response.json();
          return {
            success: false,
            error: errorData.error || 'Invalid OTP code',
          };
        }

        const data = await response.json();
        
        setIsOTPSent(false);
        setSessionId(null);
        
        return {
          success: true,
          sessionId: currentSessionId,
        };
      } catch (error) {
        console.error('Error verifying OTP:', error);
        return {
          success: false,
          error: error instanceof Error ? error.message : 'Unknown error',
        };
      } finally {
        setIsLoading(false);
      }
    },
    [sessionId]
  );

  return {
    sendOTP,
    verifyOTP,
    isLoading,
    isOTPSent,
  };
}

