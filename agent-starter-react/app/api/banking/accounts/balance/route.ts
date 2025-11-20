import { NextRequest } from 'next/server';
import { validateAccessToken, extractTokenFromHeader } from '@/lib/auth';
import { corsResponse, corsPreflight } from '@/lib/cors';
import { prisma } from '@/lib/db/prisma';

/**
 * GET /api/banking/accounts/balance
 * Retrieve account balance(s) for authenticated user
 * Optional query parameter: accountType (checking, savings, credit_card)
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

    // Parse query parameters
    const accountType = request.nextUrl.searchParams.get('accountType');

    // Validate accountType if provided
    if (accountType && !['checking', 'savings', 'credit_card'].includes(accountType)) {
      return corsResponse(
        { error: 'Invalid accountType. Must be one of: checking, savings, credit_card' },
        400
      );
    }

    // Build where clause
    const where: any = { userId: user.user_id };
    if (accountType) {
      where.accountType = accountType;
    }

    // Query accounts
    const accounts = await prisma.account.findMany({
      where,
      select: {
        id: true,
        accountNumber: true,
        accountType: true,
        balance: true,
        creditLimit: true,
        currency: true,
      },
      orderBy: { accountType: 'asc' },
    });

    // Format response with availableBalance calculation
    const balances = accounts.map((account) => {
      let availableBalance: number;
      
      if (account.accountType === 'credit_card') {
        // For credit cards: availableBalance = creditLimit - balance (available credit)
        const creditLimit = account.creditLimit ? Number(account.creditLimit) : 0;
        const balance = Number(account.balance);
        availableBalance = creditLimit - balance;
      } else {
        // For checking/savings: availableBalance = balance
        availableBalance = Number(account.balance);
      }

      return {
        accountId: account.id,
        accountNumber: account.accountNumber,
        accountType: account.accountType,
        balance: Number(account.balance),
        creditLimit: account.creditLimit ? Number(account.creditLimit) : null,
        availableBalance,
        currency: account.currency,
      };
    });

    return corsResponse({ data: balances }, 200);
  } catch (error) {
    console.error('Error fetching account balances:', error);

    if (error instanceof Error && error.message.includes('missing')) {
      return corsResponse(
        { error: 'Authorization header is required' },
        401
      );
    }

    if (error instanceof Error && (error.message.includes('Invalid') || error.message.includes('expired'))) {
      return corsResponse(
        { error: error.message },
        401
      );
    }

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


