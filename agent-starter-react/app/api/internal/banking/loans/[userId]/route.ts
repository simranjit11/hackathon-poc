import { NextRequest } from 'next/server';
import { requireApiKey } from '@/lib/api-key-auth';
import { corsResponse, corsPreflight } from '@/lib/cors';
import { prisma } from '@/lib/db/prisma';

/**
 * GET /api/internal/banking/loans/[userId]
 * Get loans for specified user (server-to-server)
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

    // Query loans for user
    const loans = await prisma.loan.findMany({
      where: { userId },
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
    return corsResponse(
      { error: error instanceof Error ? error.message : 'Internal server error' },
      500
    );
  }
}

export async function OPTIONS() {
  return corsPreflight();
}

