import { NextResponse } from 'next/server';
import { corsPreflight, corsResponse } from '@/lib/cors';
import { initializeDatabases } from '@/lib/db/init';
import { verifyOTP } from '@/lib/otp-store';

// Initialize databases on first request
let dbInitialized = false;

/**
 * POST /api/auth/2fa/verify
 * Verifies OTP code
 */
export async function POST(req: Request) {
  // Handle CORS preflight
  if (req.method === 'OPTIONS') {
    return corsPreflight();
  }

  // Initialize databases on first request
  if (!dbInitialized) {
    try {
      await initializeDatabases();
      dbInitialized = true;
    } catch (error) {
      console.error('Database initialization failed:', error);
    }
  }

  try {
    const body = await req.json();
    const { code, sessionId } = body;

    // Validate required fields
    if (!code || !sessionId) {
      return corsResponse({ error: 'Code and sessionId are required' }, 400);
    }

    // Verify OTP
    const isValid = await verifyOTP(sessionId, code);
    if (!isValid) {
      return corsResponse({ error: 'Invalid or expired OTP code' }, 400);
    }

    return corsResponse(
      {
        success: true,
        message: 'OTP verified successfully',
      },
      200
    );
  } catch (error) {
    console.error('2FA verify error:', error);
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
