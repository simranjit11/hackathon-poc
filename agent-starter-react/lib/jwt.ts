import { SignJWT } from 'jose';
import type { UserIdentity } from './auth';

/**
 * JWT token generation utilities
 */

const AUTH_SECRET_KEY = process.env.AUTH_SECRET_KEY || 'mock-secret-key-for-development-change-in-production';

/**
 * Generates a JWT access token for a user
 * 
 * @param userIdentity - User identity information
 * @param expiresIn - Token expiration time (default: 1 hour)
 * @returns Signed JWT token string
 */
export async function generateAccessToken(
  userIdentity: UserIdentity,
  expiresIn: string = '1h'
): Promise<string> {
  const secret = new TextEncoder().encode(AUTH_SECRET_KEY);
  
  const token = await new SignJWT({
    user_id: userIdentity.user_id,
    email: userIdentity.email,
    roles: userIdentity.roles,
    permissions: userIdentity.permissions,
  })
    .setProtectedHeader({ alg: 'HS256' })
    .setIssuedAt()
    .setExpirationTime(expiresIn)
    .setSubject(userIdentity.user_id) // Standard OIDC claim
    .sign(secret);

  return token;
}

/**
 * Generates a JWT token with additional claims (e.g., biometric verification)
 * 
 * @param userIdentity - User identity information
 * @param additionalClaims - Additional claims to include in token
 * @param expiresIn - Token expiration time (default: 1 hour)
 * @returns Signed JWT token string
 */
export async function generateAccessTokenWithClaims(
  userIdentity: UserIdentity,
  additionalClaims: Record<string, any> = {},
  expiresIn: string = '1h'
): Promise<string> {
  const secret = new TextEncoder().encode(AUTH_SECRET_KEY);
  
  const token = await new SignJWT({
    user_id: userIdentity.user_id,
    email: userIdentity.email,
    roles: userIdentity.roles,
    permissions: userIdentity.permissions,
    ...additionalClaims,
  })
    .setProtectedHeader({ alg: 'HS256' })
    .setIssuedAt()
    .setExpirationTime(expiresIn)
    .setSubject(userIdentity.user_id)
    .sign(secret);

  return token;
}

