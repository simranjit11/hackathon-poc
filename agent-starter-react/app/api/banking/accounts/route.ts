import { NextRequest } from 'next/server';
import { extractTokenFromHeader, validateAccessToken } from '@/lib/auth';
import { corsPreflight, corsResponse } from '@/lib/cors';
import { prisma } from '@/lib/db/prisma';

/**
 * GET /api/banking/accounts
 * Retrieve all accounts for authenticated user
 */
export async function GET(request: NextRequest) {
  // Handle CORS preflight
  if (request.method === 'OPTIONS') {
    return corsPreflight();
  }

  try {
    // Authentication
    const authHeader = request.headers.get('Authorization');
    const token = extractTokenFromHeader(authHeader);
    const user = await validateAccessToken(token);

    // Query accounts for user
    const accounts = await prisma.account.findMany({
      where: { userId: user.user_id },
      select: {
        id: true,
        accountNumber: true,
        accountType: true,
        balance: true,
        creditLimit: true,
        currency: true,
        status: true,
        createdAt: true,
      },
      orderBy: { createdAt: 'desc' },
    });

    return corsResponse({ data: accounts }, 200);
  } catch (error) {
    console.error('Error fetching accounts:', error);

    if (error instanceof Error && error.message.includes('missing')) {
      return corsResponse({ error: 'Authorization header is required' }, 401);
    }

    if (
      error instanceof Error &&
      (error.message.includes('Invalid') || error.message.includes('expired'))
    ) {
      return corsResponse({ error: error.message }, 401);
    }

    return corsResponse({ error: 'Internal server error' }, 500);
  }
}

/**
 * Handle OPTIONS request for CORS preflight
 */
export async function OPTIONS() {
  return corsPreflight();
}
