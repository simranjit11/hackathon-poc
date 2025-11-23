import { NextRequest, NextResponse } from 'next/server';
import { confirmPayment } from '@/lib/banking/payments';
import { createLatencyLogger } from '@/lib/api-latency-logger';

interface PaymentConfirmRequest {
  userId: string;
  paymentSessionId: string;
  otpCode: string;
}

const latencyLogger = createLatencyLogger('/api/internal/banking/payments/confirm', 'POST');

/**
 * POST /api/internal/banking/payments/confirm
 * Internal API: Confirm payment with OTP and complete the transaction
 * Requires API key authentication
 */
export async function POST(request: NextRequest) {
  const startTime = latencyLogger.start();
  
  const apiKey = request.headers.get('x-api-key');

  if (apiKey !== process.env.INTERNAL_API_KEY) {
    latencyLogger.end(startTime, 401);
    return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
  }

  try {
    // Parse request body
    const body: PaymentConfirmRequest = await request.json();

    // Validate required fields
    if (!body.userId || !body.paymentSessionId || !body.otpCode) {
      latencyLogger.end(startTime, 400, undefined, {
        missing_fields: {
          userId: !body.userId,
          paymentSessionId: !body.paymentSessionId,
          otpCode: !body.otpCode,
        },
      });
      return NextResponse.json(
        { error: 'userId, paymentSessionId and otpCode are required' },
        { status: 400 }
      );
    }

    // Confirm payment
    const result = await confirmPayment(body.userId, body.paymentSessionId, body.otpCode);

    latencyLogger.end(startTime, 200, undefined, {
      paymentSessionId: body.paymentSessionId,
      transactionId: result.transaction.id,
    });

    return NextResponse.json(
      {
        transaction: result.transaction,
        message: 'Payment completed successfully',
      },
      { status: 200 }
    );
  } catch (error) {
    console.error('Error confirming payment:', error);

    let statusCode = 500;
    if (error instanceof Error) {
      // Handle specific business logic errors
      if (
        error.message.includes('Invalid') ||
        error.message.includes('expired') ||
        error.message.includes('OTP')
      ) {
        statusCode = 400;
        latencyLogger.end(startTime, statusCode, error);
        return NextResponse.json({ error: error.message }, { status: statusCode });
      }
      if (error.message.includes('not found') || error.message.includes('session')) {
        statusCode = 404;
        latencyLogger.end(startTime, statusCode, error);
        return NextResponse.json({ error: error.message }, { status: statusCode });
      }
      if (error.message.includes('already processed') || error.message.includes('completed')) {
        statusCode = 409;
        latencyLogger.end(startTime, statusCode, error);
        return NextResponse.json({ error: error.message }, { status: statusCode });
      }
      if (error.message.includes('Insufficient') || error.message.includes('balance')) {
        statusCode = 400;
        latencyLogger.end(startTime, statusCode, error);
        return NextResponse.json({ error: error.message }, { status: statusCode });
      }
    }

    latencyLogger.end(startTime, statusCode, error instanceof Error ? error : new Error(String(error)));
    return NextResponse.json({ error: 'Internal server error' }, { status: statusCode });
  }
}
