import { NextRequest } from 'next/server';
import { extractTokenFromHeader, validateAccessToken } from '@/lib/auth';
import { corsPreflight, corsResponse } from '@/lib/cors';
import { prisma } from '@/lib/db/prisma';

/**
 * GET /api/banking/transactions
 * Retrieve transaction history with filtering and pagination
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
    const searchParams = request.nextUrl.searchParams;
    const accountType = searchParams.get('accountType');
    const beneficiaryId = searchParams.get('beneficiaryId');
    const transactionType = searchParams.get('transactionType');
    const startDate = searchParams.get('startDate');
    const endDate = searchParams.get('endDate');
    const limitParam = searchParams.get('limit');
    const offsetParam = searchParams.get('offset');

    // Validate pagination parameters
    const limit = limitParam ? parseInt(limitParam, 10) : 10;
    const offset = offsetParam ? parseInt(offsetParam, 10) : 0;

    if (limit < 1 || limit > 100) {
      return corsResponse({ error: 'limit must be between 1 and 100' }, 400);
    }

    if (offset < 0) {
      return corsResponse({ error: 'offset must be non-negative' }, 400);
    }

    // Validate date range
    if (startDate && endDate) {
      const start = new Date(startDate);
      const end = new Date(endDate);

      if (start > end) {
        return corsResponse({ error: 'startDate must be before endDate' }, 400);
      }

      // Check if date range exceeds 1 year
      const oneYearInMs = 365 * 24 * 60 * 60 * 1000;
      if (end.getTime() - start.getTime() > oneYearInMs) {
        return corsResponse({ error: 'Date range cannot exceed 1 year' }, 400);
      }
    }

    // Build where clause
    const where: any = { userId: user.user_id };

    // Filter by account type (requires join with account)
    if (accountType) {
      if (!['checking', 'savings', 'credit_card'].includes(accountType)) {
        return corsResponse(
          { error: 'Invalid accountType. Must be one of: checking, savings, credit_card' },
          400
        );
      }
      where.account = { accountType };
    }

    // Filter by beneficiary
    if (beneficiaryId) {
      where.beneficiaryId = beneficiaryId;
    }

    // Filter by transaction type
    if (transactionType) {
      if (!['payment', 'transfer', 'deposit', 'withdrawal'].includes(transactionType)) {
        return corsResponse(
          {
            error:
              'Invalid transactionType. Must be one of: payment, transfer, deposit, withdrawal',
          },
          400
        );
      }
      where.transactionType = transactionType;
    }

    // Filter by date range
    if (startDate || endDate) {
      where.createdAt = {};
      if (startDate) {
        where.createdAt.gte = new Date(startDate);
      }
      if (endDate) {
        where.createdAt.lte = new Date(endDate);
      }
    }

    // Get total count for pagination metadata
    const total = await prisma.transaction.count({ where });

    // Query transactions with pagination
    const transactions = await prisma.transaction.findMany({
      where,
      include: {
        beneficiary: {
          select: {
            nickname: true,
            fullName: true,
          },
        },
        account: {
          select: {
            accountType: true,
          },
        },
      },
      orderBy: { createdAt: 'desc' },
      skip: offset,
      take: limit,
    });

    // Format response
    const formattedTransactions = transactions.map((tx) => ({
      id: tx.id,
      transactionType: tx.transactionType,
      amount: Number(tx.amount),
      currency: tx.currency,
      fromAccount: tx.fromAccount,
      toAccount: tx.toAccount,
      beneficiary: tx.beneficiary
        ? {
            nickname: tx.beneficiary.nickname,
            fullName: tx.beneficiary.fullName,
          }
        : null,
      description: tx.description,
      status: tx.status,
      referenceNumber: tx.referenceNumber,
      createdAt: tx.createdAt.toISOString(),
      completedAt: tx.completedAt?.toISOString() || null,
    }));

    // Calculate pagination metadata
    const hasMore = offset + limit < total;

    return corsResponse(
      {
        data: formattedTransactions,
        meta: {
          total,
          limit,
          offset,
          hasMore,
        },
      },
      200
    );
  } catch (error) {
    console.error('Error fetching transactions:', error);

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
