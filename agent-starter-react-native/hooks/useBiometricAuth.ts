/**
 * React Native Biometric Authentication Hook
 * 
 * Provides biometric authentication functionality using expo-local-authentication
 * Supports Face ID, Touch ID, and Fingerprint authentication
 */

import { useState, useCallback, useEffect } from 'react';
import * as LocalAuthentication from 'expo-local-authentication';

export interface BiometricAuthResult {
  success: boolean;
  error?: string;
  biometricToken?: string;
}

export type BiometryType = 'FACIAL_RECOGNITION' | 'FINGERPRINT' | 'IRIS' | null;

export interface UseBiometricAuthReturn {
  isAvailable: boolean;
  biometryType: BiometryType;
  authenticate: (reason?: string) => Promise<BiometricAuthResult>;
  checkAvailability: () => Promise<void>;
  isLoading: boolean;
}

/**
 * Hook for biometric authentication
 * 
 * @returns Biometric authentication functions and state
 */
export function useBiometricAuth(): UseBiometricAuthReturn {
  const [isAvailable, setIsAvailable] = useState(false);
  const [biometryType, setBiometryType] = useState<BiometryType>(null);
  const [isLoading, setIsLoading] = useState(false);

  /**
   * Check if biometric authentication is available on the device
   */
  const checkAvailability = useCallback(async () => {
    try {
      const compatible = await LocalAuthentication.hasHardwareAsync();
      if (!compatible) {
        setIsAvailable(false);
        setBiometryType(null);
        return;
      }

      const enrolled = await LocalAuthentication.isEnrolledAsync();
      if (!enrolled) {
        setIsAvailable(false);
        setBiometryType(null);
        return;
      }

      const types = await LocalAuthentication.supportedAuthenticationTypesAsync();
      let type: BiometryType = null;
      
      if (types.includes(LocalAuthentication.AuthenticationType.FACIAL_RECOGNITION)) {
        type = 'FACIAL_RECOGNITION';
      } else if (types.includes(LocalAuthentication.AuthenticationType.FINGERPRINT)) {
        type = 'FINGERPRINT';
      } else if (types.includes(LocalAuthentication.AuthenticationType.IRIS)) {
        type = 'IRIS';
      }

      setIsAvailable(true);
      setBiometryType(type);
    } catch (error) {
      console.error('Error checking biometric availability:', error);
      setIsAvailable(false);
      setBiometryType(null);
    }
  }, []);

  // Check availability on mount
  useEffect(() => {
    checkAvailability();
  }, [checkAvailability]);

  /**
   * Authenticate using biometrics
   * 
   * @param reason - Optional reason message for the biometric prompt
   * @returns Authentication result with success status and optional biometric token
   */
  const authenticate = useCallback(
    async (reason?: string): Promise<BiometricAuthResult> => {
      setIsLoading(true);
      try {
        // Check if biometrics are available
        const compatible = await LocalAuthentication.hasHardwareAsync();
        if (!compatible) {
          return {
            success: false,
            error: 'Biometric authentication not available on this device',
          };
        }

        const enrolled = await LocalAuthentication.isEnrolledAsync();
        if (!enrolled) {
          return {
            success: false,
            error: 'No biometric credentials enrolled on this device',
          };
        }

        // Authenticate with biometrics
        const result = await LocalAuthentication.authenticateAsync({
          promptMessage: reason || 'Authenticate to continue',
          cancelLabel: 'Cancel',
          disableDeviceFallback: false,
        });

        if (result.success) {
          // Generate a biometric token
          // In production, this would be sent to your auth service
          // For now, we'll create a simple token based on the authentication result
          const token = `biometric_${Date.now()}_${Math.random().toString(36).substring(2, 9)}`;
          return {
            success: true,
            biometricToken: token,
          };
        } else {
          return {
            success: false,
            error: result.error === 'user_cancel' 
              ? 'Biometric authentication cancelled' 
              : 'Biometric authentication failed',
          };
        }
      } catch (error) {
        console.error('Biometric authentication error:', error);
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

  return {
    isAvailable,
    biometryType,
    authenticate,
    checkAvailability,
    isLoading,
  };
}

/**
 * Check if biometric authentication is supported and available
 * 
 * @returns Promise resolving to availability status and biometry type
 */
export async function checkBiometricAvailability(): Promise<{
  available: boolean;
  biometryType: BiometryType;
}> {
  try {
    const compatible = await LocalAuthentication.hasHardwareAsync();
    if (!compatible) {
      return { available: false, biometryType: null };
    }

    const enrolled = await LocalAuthentication.isEnrolledAsync();
    if (!enrolled) {
      return { available: false, biometryType: null };
    }

    const types = await LocalAuthentication.supportedAuthenticationTypesAsync();
    let type: BiometryType = null;
    
    if (types.includes(LocalAuthentication.AuthenticationType.FACIAL_RECOGNITION)) {
      type = 'FACIAL_RECOGNITION';
    } else if (types.includes(LocalAuthentication.AuthenticationType.FINGERPRINT)) {
      type = 'FINGERPRINT';
    } else if (types.includes(LocalAuthentication.AuthenticationType.IRIS)) {
      type = 'IRIS';
    }

    return { available: true, biometryType: type };
  } catch (error) {
    console.error('Error checking biometric availability:', error);
    return { available: false, biometryType: null };
  }
}

