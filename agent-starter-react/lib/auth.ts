import { jwtVerify } from 'jose';

/**
 * User identity extracted from access token
 */
export interface UserIdentity {
    user_id: string;
    email: string;
    roles: string[];
    permissions: string[];
}

/**
 * Validates an access token and extracts user identity
 * 
 * In production, this would validate against an OAuth/OIDC provider.
 * For now, this is a mock implementation that validates JWT tokens.
 * 
 * @param token - The access token from Authorization header
 * @returns User identity if token is valid
 * @throws Error if token is invalid or expired
 */
export async function validateAccessToken(token: string): Promise<UserIdentity> {
    try {
        // In production, this would fetch the JWKS from your OAuth/OIDC provider
        // For now, we'll use a mock secret key from environment variables
        const secret = process.env.AUTH_SECRET_KEY || 'mock-secret-key-for-development';

        // Decode and verify the token
        const { payload } = await jwtVerify(token, new TextEncoder().encode(secret), {
            algorithms: ['HS256'],
        });

        // Extract user identity from token claims
        // Standard OIDC claims: sub (user_id), email, roles, permissions
        const user_id = payload.sub || payload.user_id || payload.userId;
        const email = payload.email as string;
        const roles = (payload.roles as string[]) || (payload.role ? [payload.role as string] : ['customer']);
        const permissions = (payload.permissions as string[]) || (payload.scope ? (payload.scope as string).split(' ') : ['read']);

        if (!user_id || !email) {
            throw new Error('Token missing required claims: user_id and email');
        }

        return {
            user_id: String(user_id),
            email: String(email),
            roles: Array.isArray(roles) ? roles : [roles],
            permissions: Array.isArray(permissions) ? permissions : [permissions],
        };
    } catch (error) {
        if (error instanceof Error) {
            throw new Error(`Token validation failed: ${error.message}`);
        }
        throw new Error('Token validation failed: Unknown error');
    }
}

/**
 * Extracts the access token from the Authorization header
 * 
 * @param authHeader - The Authorization header value (e.g., "Bearer <token>")
 * @returns The token string
 * @throws Error if header is missing or malformed
 */
export function extractTokenFromHeader(authHeader: string | null): string {
    if (!authHeader) {
        throw new Error('Authorization header is missing');
    }

    if (!authHeader.startsWith('Bearer ')) {
        throw new Error('Authorization header must start with "Bearer "');
    }

    const token = authHeader.substring(7).trim();
    if (!token) {
        throw new Error('Token is missing from Authorization header');
    }

    return token;
}

/**
 * Gets the access token from client storage
 * In production, this would retrieve from secure storage or OAuth provider
 * 
 * @returns The access token or null if not available
 */
export function getAccessToken(): string | null {
    // In production, this would integrate with your OAuth/OIDC provider
    // For now, check localStorage for a stored token
    if (typeof window !== 'undefined') {
        return localStorage.getItem('access_token');
    }
    return null;
}

/**
 * Sets the access token in client storage
 * 
 * @param token - The access token to store
 */
export function setAccessToken(token: string): void {
    if (typeof window !== 'undefined') {
        localStorage.setItem('access_token', token);
    }
}

/**
 * Removes the access token from client storage
 */
export function clearAccessToken(): void {
    if (typeof window !== 'undefined') {
        localStorage.removeItem('access_token');
    }
}

