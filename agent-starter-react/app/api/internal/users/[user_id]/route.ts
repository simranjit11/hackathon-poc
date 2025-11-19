import { NextRequest, NextResponse } from 'next/server';
import { requireApiKey } from '@/lib/api-key-auth';
import { findUserById } from '@/lib/users';
import { corsResponse, corsPreflight } from '@/lib/cors';

/**
 * GET /api/internal/users/[user_id]
 * 
 * Server-to-server endpoint to get user details by user_id.
 * Requires API key authentication (X-API-Key header).
 * 
 * Used by MCP server and other backend services to retrieve
 * user information like email, phone number, etc.
 */
export async function GET(
  request: NextRequest,
  { params }: { params: { user_id: string } }
) {
  // Handle CORS preflight
  if (request.method === 'OPTIONS') {
    return corsPreflight();
  }

  // Require API key authentication
  const authError = requireApiKey(request);
  if (authError) {
    return authError;
  }

  try {
    const { user_id } = params;

    if (!user_id) {
      return corsResponse(
        { error: 'user_id is required' },
        400
      );
    }

    // Get user details
    const user = await findUserById(user_id);
    
    if (!user) {
      return corsResponse(
        { error: 'User not found' },
        404
      );
    }

    // Return user information (including sensitive fields for internal use)
    return corsResponse({
      user: {
        id: user.id,
        email: user.email,
        name: user.name || null,
        roles: user.roles,
        permissions: user.permissions,
        createdAt: user.createdAt.toISOString(),
        lastLoginAt: user.lastLoginAt?.toISOString() || null,
        // Note: Phone number can be added to User schema if needed
      },
    }, 200);
  } catch (error) {
    console.error('Error fetching user details:', error);
    return corsResponse(
      { error: error instanceof Error ? error.message : 'Internal server error' },
      500
    );
  }
}

/**
 * Handle OPTIONS request for CORS preflight
 */
export async function OPTIONS() {
  return corsPreflight();
}

