import { NextResponse } from 'next/server';
import { corsResponse, corsPreflight } from '@/lib/cors';

/**
 * POST /api/auth/logout
 * Logs out a user (client should clear token)
 * 
 * Note: Since we're using stateless JWTs, logout is primarily client-side.
 * In production, you might want to maintain a token blacklist in Redis.
 */
export async function POST(req: Request) {
  // Handle CORS preflight
  if (req.method === 'OPTIONS') {
    return corsPreflight();
  }

  try {
    // In a stateless JWT system, logout is handled client-side
    // The client should remove the token from storage
    // Optionally, we could maintain a token blacklist in Redis for production
    
    return corsResponse(
      { message: 'Logged out successfully' },
      200
    );
  } catch (error) {
    console.error('Logout error:', error);
    return corsResponse(
      { error: 'Internal server error' },
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

