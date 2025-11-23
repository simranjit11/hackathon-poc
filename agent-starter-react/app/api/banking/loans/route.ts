import { NextRequest } from 'next/server';
import { extractTokenFromHeader, validateAccessToken } from '@/lib/auth';
import { corsPreflight, corsResponse } from '@/lib/cors';
import { prisma } from '@/lib/db/prisma';

/**
 * GET /api/banking/loans
 * Retrieve all loans for authenticated user
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

    // Query loans for user
    const loans = await prisma.loan.findMany({
      where: { userId: user.user_id },
      select: {
        id: true,
        loanType: true,
        loanNumber: true,
        outstandingBalance: true,
        interestRate: true,
        monthlyPayment: true,
        remainingTermMonths: true,
        nextPaymentDate: true,
        accountId: true,
        createdAt: true,
      },
      orderBy: { createdAt: 'desc' },
    });

    // Format response with proper number conversion
    const formattedLoans = loans.map((loan) => ({
      id: loan.id,
      loanType: loan.loanType,
      loanNumber: loan.loanNumber,
      outstandingBalance: Number(loan.outstandingBalance),
      interestRate: Number(loan.interestRate),
      monthlyPayment: Number(loan.monthlyPayment),
      remainingTermMonths: loan.remainingTermMonths,
      nextPaymentDate: loan.nextPaymentDate.toISOString(),
      accountId: loan.accountId,
      createdAt: loan.createdAt.toISOString(),
    }));

    return corsResponse({ data: formattedLoans }, 200);
  } catch (error) {
    console.error('Error fetching loans:', error);

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
