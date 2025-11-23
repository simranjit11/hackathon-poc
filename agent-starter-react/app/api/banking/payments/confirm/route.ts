import { NextRequest } from 'next/server';
import { extractTokenFromHeader, validateAccessToken } from '@/lib/auth';
import { confirmPayment } from '@/lib/banking/payments';
import { corsPreflight, corsResponse } from '@/lib/cors';

interface PaymentConfirmRequest {
  paymentSessionId: string;
  otpCode: string;
}

/**
 * POST /api/banking/payments/confirm
 * Confirm payment with OTP and complete the transaction
 */
export async function POST(request: NextRequest) {
  // Handle CORS preflight
  if (request.method === 'OPTIONS') {
    return corsPreflight();
  }

  try {
    // Authentication
    const authHeader = request.headers.get('Authorization');
    const token = extractTokenFromHeader(authHeader);
    const user = await validateAccessToken(token);

    // Check transact permission
    if (!user.permissions.includes('transact')) {
      return corsResponse(
        { error: 'Insufficient permissions. transact permission required.' },
        403
      );
    }

    // Parse request body
    const body: PaymentConfirmRequest = await request.json();

    // Validate required fields
    if (!body.paymentSessionId || !body.otpCode) {
      return corsResponse({ error: 'paymentSessionId and otpCode are required' }, 400);
    }

    // Confirm payment
    const result = await confirmPayment(user.user_id, body.paymentSessionId, body.otpCode);

    return corsResponse(
      {
        transaction: result.transaction,
        message: 'Payment completed successfully',
      },
      200
    );
  } catch (error) {
    console.error('Error confirming payment:', error);

    if (error instanceof Error && error.message.includes('missing')) {
      return corsResponse({ error: 'Authorization header is required' }, 401);
    }

    if (
      error instanceof Error &&
      (error.message.includes('Invalid') || error.message.includes('expired'))
    ) {
      // Check if it's an auth error or OTP error
      if (error.message.includes('OTP') || error.message.includes('expired')) {
        return corsResponse({ error: error.message }, 400);
      }
      return corsResponse({ error: error.message }, 401);
    }

    if (error instanceof Error) {
      // Handle specific business logic errors
      if (error.message.includes('not found') || error.message.includes('session')) {
        return corsResponse({ error: error.message }, 404);
      }
      if (error.message.includes('already processed') || error.message.includes('completed')) {
        return corsResponse({ error: error.message }, 409);
      }
      if (error.message.includes('Insufficient') || error.message.includes('expired')) {
        return corsResponse({ error: error.message }, 400);
      }
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
