import { NextRequest } from 'next/server';
import { validateAccessToken, extractTokenFromHeader } from '@/lib/auth';
import { corsResponse, corsPreflight } from '@/lib/cors';
import { prisma } from '@/lib/db/prisma';

const VALID_ALERT_TYPES = ['payment_received', 'payment_sent', 'low_balance', 'high_balance'];

/**
 * GET /api/banking/alerts
 * Retrieve all payment alerts for authenticated user
 */
export async function GET(request: NextRequest) {
  if (request.method === 'OPTIONS') {
    return corsPreflight();
  }

  try {
    const authHeader = request.headers.get('Authorization');
    const token = extractTokenFromHeader(authHeader);
    const user = await validateAccessToken(token);

    const alerts = await prisma.paymentAlert.findMany({
      where: { userId: user.user_id },
      select: {
        id: true,
        alertType: true,
        threshold: true,
        accountId: true,
        isActive: true,
        createdAt: true,
        updatedAt: true,
      },
      orderBy: { createdAt: 'desc' },
    });

    return corsResponse(
      {
        data: alerts.map((alert) => ({
          id: alert.id,
          alertType: alert.alertType,
          threshold: alert.threshold ? Number(alert.threshold) : null,
          accountId: alert.accountId,
          isActive: alert.isActive,
          createdAt: alert.createdAt.toISOString(),
          updatedAt: alert.updatedAt.toISOString(),
        })),
      },
      200
    );
  } catch (error) {
    console.error('Error fetching alerts:', error);

    if (error instanceof Error && error.message.includes('missing')) {
      return corsResponse({ error: 'Authorization header is required' }, 401);
    }

    if (error instanceof Error && (error.message.includes('Invalid') || error.message.includes('expired'))) {
      return corsResponse({ error: error.message }, 401);
    }

    return corsResponse({ error: 'Internal server error' }, 500);
  }
}

/**
 * POST /api/banking/alerts
 * Create a new payment alert
 */
export async function POST(request: NextRequest) {
  if (request.method === 'OPTIONS') {
    return corsPreflight();
  }

  try {
    const authHeader = request.headers.get('Authorization');
    const token = extractTokenFromHeader(authHeader);
    const user = await validateAccessToken(token);

    const body = await request.json();
    const { alertType, threshold, accountId } = body;

    // Validate alertType
    if (!alertType || !VALID_ALERT_TYPES.includes(alertType)) {
      return corsResponse(
        { error: `alertType must be one of: ${VALID_ALERT_TYPES.join(', ')}` },
        400
      );
    }

    // Validate threshold for balance-based alerts
    if (alertType === 'low_balance' || alertType === 'high_balance') {
      if (!threshold || threshold <= 0) {
        return corsResponse(
          { error: 'threshold is required and must be positive for balance-based alerts' },
          400
        );
      }
    }

    // Validate account ownership if accountId provided
    if (accountId) {
      const account = await prisma.account.findFirst({
        where: {
          id: accountId,
          userId: user.user_id,
        },
      });

      if (!account) {
        return corsResponse(
          { error: 'Account not found or does not belong to user' },
          404
        );
      }
    }

    // Create alert
    const alert = await prisma.paymentAlert.create({
      data: {
        userId: user.user_id,
        alertType,
        threshold: threshold ? threshold : null,
        accountId: accountId || null,
        isActive: true,
      },
    });

    return corsResponse(
      {
        data: {
          id: alert.id,
          alertType: alert.alertType,
          threshold: alert.threshold ? Number(alert.threshold) : null,
          accountId: alert.accountId,
          isActive: alert.isActive,
          createdAt: alert.createdAt.toISOString(),
          updatedAt: alert.updatedAt.toISOString(),
        },
      },
      201
    );
  } catch (error) {
    console.error('Error creating alert:', error);

    if (error instanceof Error && error.message.includes('missing')) {
      return corsResponse({ error: 'Authorization header is required' }, 401);
    }

    if (error instanceof Error && (error.message.includes('Invalid') || error.message.includes('expired'))) {
      return corsResponse({ error: error.message }, 401);
    }

    return corsResponse({ error: 'Internal server error' }, 500);
  }
}

export async function OPTIONS() {
  return corsPreflight();
}


