import { getRedisClient } from './db/redis';

/**
 * OTP storage using Redis
 * Provides TTL-based expiration for OTP codes
 */

interface OTPEntry {
  code: string;
  expiresAt: number;
}

/**
 * Store an OTP code in Redis
 *
 * @param sessionId - Session identifier
 * @param code - OTP code
 * @param ttlSeconds - Time to live in seconds (default: 5 minutes)
 */
export async function storeOTP(
  sessionId: string,
  code: string,
  ttlSeconds: number = 300
): Promise<void> {
  const redis = getRedisClient();
  const key = `otp:${sessionId}`;

  const data: OTPEntry = {
    code,
    expiresAt: Date.now() + ttlSeconds * 1000,
  };

  await redis.setex(key, ttlSeconds, JSON.stringify(data));
}

/**
 * Get and verify an OTP code from Redis
 *
 * @param sessionId - Session identifier
 * @param code - OTP code to verify
 * @returns True if code is valid, false otherwise
 */
export async function verifyOTP(sessionId: string, code: string): Promise<boolean> {
  const redis = getRedisClient();
  const key = `otp:${sessionId}`;

  try {
    const dataStr = await redis.get(key);
    if (!dataStr) {
      return false; // OTP not found or expired
    }

    const data: OTPEntry = JSON.parse(dataStr);

    // Check expiration (additional check, Redis TTL should handle this)
    if (data.expiresAt < Date.now()) {
      await redis.del(key); // Clean up expired entry
      return false;
    }

    // Verify code
    if (data.code !== code) {
      return false;
    }

    // Remove used OTP
    await redis.del(key);
    return true;
  } catch (error) {
    console.error('Error verifying OTP:', error);
    return false;
  }
}

/**
 * Get OTP entry (for debugging)
 *
 * @param sessionId - Session identifier
 * @returns OTP entry or null
 */
export async function getOTP(sessionId: string): Promise<OTPEntry | null> {
  const redis = getRedisClient();
  const key = `otp:${sessionId}`;

  try {
    const dataStr = await redis.get(key);
    if (!dataStr) {
      return null;
    }

    const data: OTPEntry = JSON.parse(dataStr);

    // Check expiration
    if (data.expiresAt < Date.now()) {
      await redis.del(key);
      return null;
    }

    return data;
  } catch (error) {
    console.error('Error getting OTP:', error);
    return null;
  }
}

/**
 * Clear all OTPs (for testing)
 * Note: This clears ALL OTP keys - use with caution!
 */
export async function clearAllOTPs(): Promise<void> {
  const redis = getRedisClient();

  try {
    const keys = await redis.keys('otp:*');
    if (keys.length > 0) {
      await redis.del(...keys);
    }
  } catch (error) {
    console.error('Error clearing OTPs:', error);
    throw error;
  }
}

/**
 * Get remaining TTL for an OTP
 *
 * @param sessionId - Session identifier
 * @returns TTL in seconds, or -1 if not found
 */
export async function getOTPTTL(sessionId: string): Promise<number> {
  const redis = getRedisClient();
  const key = `otp:${sessionId}`;

  try {
    return await redis.ttl(key);
  } catch (error) {
    console.error('Error getting OTP TTL:', error);
    return -1;
  }
}
