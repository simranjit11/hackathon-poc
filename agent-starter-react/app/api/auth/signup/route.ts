import { NextResponse } from 'next/server';
import { corsPreflight, corsResponse } from '@/lib/cors';
import { initializeDatabases } from '@/lib/db/init';
import { generateAccessToken } from '@/lib/jwt';
import { createUser, userToIdentity } from '@/lib/users';

/**
 * Signup request body
 */
interface SignupRequest {
  email: string;
  password: string;
  name?: string;
}

/**
 * Signup response
 */
interface SignupResponse {
  accessToken: string;
  user: {
    id: string;
    email: string;
    name?: string;
    roles: string[];
    permissions: string[];
  };
}

/**
 * POST /api/auth/signup
 * Creates a new user account and returns an access token
 */
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
    const body: SignupRequest = await req.json();
    const { email, password, name } = body;

    // Validate required fields
    if (!email || !password) {
      return corsResponse({ error: 'Email and password are required' }, 400);
    }

    // Validate email format
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!emailRegex.test(email)) {
      return corsResponse({ error: 'Invalid email format' }, 400);
    }

    // Validate password strength (minimum 8 characters)
    if (password.length < 8) {
      return corsResponse({ error: 'Password must be at least 8 characters long' }, 400);
    }

    // Create user
    let user;
    try {
      user = await createUser(email, password, ['customer'], ['read'], name);
    } catch (error) {
      if (error instanceof Error && error.message === 'User already exists') {
        return corsResponse({ error: 'An account with this email already exists' }, 409);
      }
      throw error;
    }

    // Generate access token
    const userIdentity = userToIdentity(user);
    const accessToken = await generateAccessToken(userIdentity);

    const response: SignupResponse = {
      accessToken,
      user: {
        id: user.id,
        email: user.email,
        name: user.name || undefined,
        roles: user.roles,
        permissions: user.permissions,
      },
    };

    return corsResponse(response, 201);
  } catch (error) {
    console.error('Signup error:', error);
    return corsResponse({ error: 'Failed to create account. Please try again.' }, 500);
  }
}

export async function OPTIONS() {
  return corsPreflight();
}
