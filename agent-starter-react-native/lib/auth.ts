/**
 * Authentication utilities for React Native mobile app
 * Handles access token storage and retrieval
 */

import AsyncStorage from '@react-native-async-storage/async-storage';

const ACCESS_TOKEN_KEY = 'access_token';

/**
 * Gets the access token from secure storage
 * 
 * @returns The access token or null if not available
 */
export async function getAccessToken(): Promise<string | null> {
  try {
    return await AsyncStorage.getItem(ACCESS_TOKEN_KEY);
  } catch (error) {
    console.error('Error retrieving access token:', error);
    return null;
  }
}

/**
 * Sets the access token in secure storage
 * 
 * @param token - The access token to store
 */
export async function setAccessToken(token: string): Promise<void> {
  try {
    await AsyncStorage.setItem(ACCESS_TOKEN_KEY, token);
  } catch (error) {
    console.error('Error storing access token:', error);
    throw error;
  }
}

/**
 * Removes the access token from secure storage
 */
export async function clearAccessToken(): Promise<void> {
  try {
    await AsyncStorage.removeItem(ACCESS_TOKEN_KEY);
  } catch (error) {
    console.error('Error clearing access token:', error);
  }
}

