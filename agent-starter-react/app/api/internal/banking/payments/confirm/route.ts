import { NextRequest, NextResponse } from 'next/server';
import { confirmPayment } from '@/lib/banking/payments';

interface PaymentConfirmRequest {
  userId: string;
  paymentSessionId: string;
  otpCode: string;
}

/**
 * POST /api/internal/banking/payments/confirm
 * Internal API: Confirm payment with OTP and complete the transaction
 * Requires API key authentication
 */
export async function POST(request: NextRequest) {
  const apiKey = request.headers.get('x-api-key');

  if (apiKey !== process.env.INTERNAL_API_KEY) {
    return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
  }

  try {
    // Parse request body
    const body: PaymentConfirmRequest = await request.json();

    // Validate required fields
    if (!body.userId || !body.paymentSessionId || !body.otpCode) {
      return NextResponse.json(
        { error: 'userId, paymentSessionId and otpCode are required' },
        { status: 400 }
      );
    }

    // Confirm payment
    const result = await confirmPayment(
      body.userId,
      body.paymentSessionId,
      body.otpCode
    );

    return NextResponse.json(
      {
        transaction: result.transaction,
        message: 'Payment completed successfully',
      },
      { status: 200 }
    );
  } catch (error) {
    console.error('Error confirming payment:', error);

    if (error instanceof Error) {
      // Handle specific business logic errors
      if (error.message.includes('Invalid') || error.message.includes('expired') || error.message.includes('OTP')) {
        return NextResponse.json(
          { error: error.message },
          { status: 400 }
        );
      }
      if (error.message.includes('not found') || error.message.includes('session')) {
        return NextResponse.json(
          { error: error.message },
          { status: 404 }
        );
      }
      if (error.message.includes('already processed') || error.message.includes('completed')) {
        return NextResponse.json(
          { error: error.message },
          { status: 409 }
        );
      }
      if (error.message.includes('Insufficient') || error.message.includes('balance')) {
        return NextResponse.json(
          { error: error.message },
          { status: 400 }
        );
      }
    }

    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    );
  }
}

