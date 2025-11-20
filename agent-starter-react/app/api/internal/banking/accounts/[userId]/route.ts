import { NextRequest } from 'next/server';
import { requireApiKey } from '@/lib/api-key-auth';
import { corsResponse, corsPreflight } from '@/lib/cors';
import { prisma } from '@/lib/db/prisma';

/**
 * GET /api/internal/banking/accounts/[userId]
 * Get accounts for specified user (server-to-server)
 * Requires API key authentication
 */
export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ userId: string }> }
) {
  if (request.method === 'OPTIONS') {
    return corsPreflight();
  }

  // Require API key authentication
  const authError = requireApiKey(request);
  if (authError) {
    return authError;
  }

  try {
    const { userId } = await params;

    if (!userId) {
      return corsResponse({ error: 'userId is required' }, 400);
    }

    // Verify user exists
    const user = await prisma.user.findUnique({
      where: { id: userId },
    });

    if (!user) {
      return corsResponse({ error: 'User not found' }, 404);
    }

    // Query accounts for user
    const accounts = await prisma.account.findMany({
      where: { userId },
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
    return corsResponse(
      { error: error instanceof Error ? error.message : 'Internal server error' },
      500
    );
  }
}

export async function OPTIONS() {
  return corsPreflight();
}


