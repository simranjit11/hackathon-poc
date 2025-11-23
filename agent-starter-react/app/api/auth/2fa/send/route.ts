import { NextResponse } from 'next/server';
import { corsPreflight, corsResponse } from '@/lib/cors';
import { initializeDatabases } from '@/lib/db/init';
import { storeOTP } from '@/lib/otp-store';

/**
 * Generate a 6-digit OTP code
 */
function generateOTP(): string {
  return Math.floor(100000 + Math.random() * 900000).toString();
}

// Initialize databases on first request
let dbInitialized = false;

/**
 * POST /api/auth/2fa/send
 * Sends OTP code via SMS or Email
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
    const { method, phoneOrEmail } = body;

    // Validate required fields
    if (!method || !phoneOrEmail) {
      return corsResponse({ error: 'Method and phoneOrEmail are required' }, 400);
    }

    if (method !== 'sms' && method !== 'email') {
      return corsResponse({ error: 'Method must be "sms" or "email"' }, 400);
    }

    // Generate OTP
    const otpCode = generateOTP();
    const sessionId = `otp_${Date.now()}_${Math.random().toString(36).substring(2, 9)}`;

    // Store OTP in Redis
    await storeOTP(sessionId, otpCode, 300); // 5 minutes TTL

    // In production, send OTP via SMS/Email service
    // For hackathon, log it (in production, never log OTPs!)
    console.log(`[DEV ONLY] OTP for ${phoneOrEmail}: ${otpCode} (session: ${sessionId})`);

    return corsResponse(
      {
        sessionId,
        message: `OTP sent to ${method === 'sms' ? 'phone' : 'email'}`,
        // In production, don't return the OTP!
        // For hackathon testing, include it in dev mode only
        ...(process.env.NODE_ENV === 'development' && { otpCode }),
      },
      200
    );
  } catch (error) {
    console.error('2FA send error:', error);
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
