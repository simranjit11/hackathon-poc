import { NextResponse } from 'next/server';
import { corsPreflight, corsResponse } from '@/lib/cors';
import { initializeDatabases } from '@/lib/db/init';
import { generateAccessTokenWithClaims } from '@/lib/jwt';
import { userToIdentity, validateCredentials } from '@/lib/users';

/**
 * Login request body
 */
interface LoginRequest {
  email: string;
  password: string;
  biometricToken?: string; // Optional, mobile only
  otpCode?: string; // Optional, web only
}

/**
 * Login response
 */
interface LoginResponse {
  accessToken: string;
  user: {
    id: string;
    email: string;
    roles: string[];
    permissions: string[];
    name?: string;
  };
}

/**
 * POST /api/auth/login
 * Authenticates a user and returns an access token
 * Supports both web and mobile clients
 */
// Initialize databases on first request (in production, do this on app startup)
let dbInitialized = false;

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
      // Continue anyway - might be a connection issue
    }
  }

  try {
    const body: LoginRequest = await req.json();
    const { email, password, biometricToken, otpCode } = body;

    // Validate required fields
    if (!email || !password) {
      return corsResponse({ error: 'Email and password are required' }, 400);
    }

    // Validate credentials
    const user = await validateCredentials(email, password);
    if (!user) {
      return corsResponse({ error: 'Invalid email or password' }, 401);
    }

    // Validate biometric token if provided (mobile)
    if (biometricToken) {
      // In production, validate biometric token against auth service
      // For hackathon, just check that it's present and has expected format
      if (!biometricToken.startsWith('biometric_')) {
        return corsResponse({ error: 'Invalid biometric token' }, 401);
      }
    }

    // Validate OTP if provided (web)
    if (otpCode) {
      // In production, validate OTP against stored session
      // For hackathon, accept any 6-digit code
      if (!/^\d{6}$/.test(otpCode)) {
        return corsResponse({ error: 'Invalid OTP code format' }, 400);
      }
    }

    // Generate access token with additional claims
    const userIdentity = userToIdentity(user);
    const additionalClaims: Record<string, any> = {};

    if (biometricToken) {
      additionalClaims.biometric_verified = true;
      additionalClaims.platform = 'mobile';
    }

    if (otpCode) {
      additionalClaims.two_factor_verified = true;
      additionalClaims.platform = 'web';
    }

    const accessToken = await generateAccessTokenWithClaims(userIdentity, additionalClaims);

    // Return success response
    const response: LoginResponse = {
      accessToken,
      user: {
        id: user.id,
        email: user.email,
        roles: user.roles,
        permissions: user.permissions,
        name: user.name ?? undefined,
      },
    };

    return corsResponse(response, 200);
  } catch (error) {
    console.error('Login error:', error);
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
