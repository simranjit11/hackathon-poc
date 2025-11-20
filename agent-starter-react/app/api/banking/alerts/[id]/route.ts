import { NextRequest } from 'next/server';
import { validateAccessToken, extractTokenFromHeader } from '@/lib/auth';
import { corsResponse, corsPreflight } from '@/lib/cors';
import { prisma } from '@/lib/db/prisma';

const VALID_ALERT_TYPES = ['payment_received', 'payment_sent', 'low_balance', 'high_balance'];

/**
 * PUT /api/banking/alerts/[id]
 * Update an existing payment alert
 */
export async function PUT(
  request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  if (request.method === 'OPTIONS') {
    return corsPreflight();
  }

  try {
    const authHeader = request.headers.get('Authorization');
    const token = extractTokenFromHeader(authHeader);
    const user = await validateAccessToken(token);

    const { id } = await params;
    const body = await request.json();

    // Verify alert belongs to user
    const existingAlert = await prisma.paymentAlert.findFirst({
      where: {
        id,
        userId: user.user_id,
      },
    });

    if (!existingAlert) {
      return corsResponse({ error: 'Alert not found' }, 404);
    }

    // Validate alertType if provided
    if (body.alertType && !VALID_ALERT_TYPES.includes(body.alertType)) {
      return corsResponse(
        { error: `alertType must be one of: ${VALID_ALERT_TYPES.join(', ')}` },
        400
      );
    }

    // Validate threshold for balance-based alerts
    const alertType = body.alertType || existingAlert.alertType;
    if ((alertType === 'low_balance' || alertType === 'high_balance') && body.threshold !== undefined) {
      if (body.threshold === null || body.threshold <= 0) {
        return corsResponse(
          { error: 'threshold is required and must be positive for balance-based alerts' },
          400
        );
      }
    }

    // Validate account ownership if accountId provided
    if (body.accountId !== undefined) {
      if (body.accountId) {
        const account = await prisma.account.findFirst({
          where: {
            id: body.accountId,
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
    }

    // Update alert
    const updatedAlert = await prisma.paymentAlert.update({
      where: { id },
      data: {
        alertType: body.alertType,
        threshold: body.threshold !== undefined ? body.threshold : undefined,
        accountId: body.accountId !== undefined ? body.accountId : undefined,
        isActive: body.isActive !== undefined ? body.isActive : undefined,
      },
    });

    return corsResponse(
      {
        data: {
          id: updatedAlert.id,
          alertType: updatedAlert.alertType,
          threshold: updatedAlert.threshold ? Number(updatedAlert.threshold) : null,
          accountId: updatedAlert.accountId,
          isActive: updatedAlert.isActive,
          createdAt: updatedAlert.createdAt.toISOString(),
          updatedAt: updatedAlert.updatedAt.toISOString(),
        },
      },
      200
    );
  } catch (error) {
    console.error('Error updating alert:', error);

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
 * DELETE /api/banking/alerts/[id]
 * Delete a payment alert
 */
export async function DELETE(
  request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  if (request.method === 'OPTIONS') {
    return corsPreflight();
  }

  try {
    const authHeader = request.headers.get('Authorization');
    const token = extractTokenFromHeader(authHeader);
    const user = await validateAccessToken(token);

    const { id } = await params;

    // Verify alert belongs to user
    const alert = await prisma.paymentAlert.findFirst({
      where: {
        id,
        userId: user.user_id,
      },
    });

    if (!alert) {
      return corsResponse({ error: 'Alert not found' }, 404);
    }

    // Delete alert
    await prisma.paymentAlert.delete({
      where: { id },
    });

    return new NextResponse(null, { status: 204 });
  } catch (error) {
    console.error('Error deleting alert:', error);

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


