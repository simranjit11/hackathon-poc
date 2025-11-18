import { NextResponse } from 'next/server';
import { validateAccessToken, extractTokenFromHeader } from '@/lib/auth';
import { findUserById } from '@/lib/users';
import { corsResponse, corsPreflight } from '@/lib/cors';

/**
 * GET /api/auth/me
 * Validates token and returns current user information
 */
export async function GET(req: Request) {
  // Handle CORS preflight
  if (req.method === 'OPTIONS') {
    return corsPreflight();
  }

  try {
    // Extract and validate token
    const authHeader = req.headers.get('Authorization');
    const token = extractTokenFromHeader(authHeader);
    const userIdentity = await validateAccessToken(token);

    // Get full user details
    const user = await findUserById(userIdentity.user_id);
    if (!user) {
      return corsResponse(
        { error: 'User not found' },
        404
      );
    }

    // Return user information
    return corsResponse({
      user: {
        id: user.id,
        email: user.email,
        roles: user.roles,
        permissions: user.permissions,
        name: user.name,
      },
    }, 200);
  } catch (error) {
    console.error('Token validation error:', error);
    
    if (error instanceof Error && error.message.includes('missing')) {
      return corsResponse(
        { error: 'Authorization header is required' },
        401
      );
    }

    return corsResponse(
      { error: error instanceof Error ? error.message : 'Invalid or expired token' },
      401
    );
  }
}

/**
 * Handle OPTIONS request for CORS preflight
 */
export async function OPTIONS() {
  return corsPreflight();
}

