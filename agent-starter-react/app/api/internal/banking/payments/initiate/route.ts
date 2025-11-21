import { NextRequest, NextResponse } from 'next/server';
import { initiatePayment, PaymentInitiationOptions } from '@/lib/banking/payments';

interface PaymentInitiateRequest {
  userId: string;
  fromAccount: string;
  beneficiaryId?: string;
  beneficiaryNickname?: string;
  paymentAddress?: string;
  toAccount?: string;
  amount: number;
  description?: string;
}

/**
 * POST /api/internal/banking/payments/initiate
 * Internal API: Initiate a payment and generate OTP for confirmation
 * Requires API key authentication
 */
export async function POST(request: NextRequest) {
  const apiKey = request.headers.get('x-api-key');

  if (apiKey !== process.env.INTERNAL_API_KEY) {
    return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
  }

  try {
    // Parse request body
    const body: PaymentInitiateRequest = await request.json();

    // Validate required fields
    if (!body.userId || !body.fromAccount || !body.amount) {
      return NextResponse.json(
        { error: 'userId, fromAccount and amount are required' },
        { status: 400 }
      );
    }

    // Build payment options
    const options: PaymentInitiationOptions = {};
    if (body.beneficiaryId) {
      options.beneficiaryId = body.beneficiaryId;
    }
    if (body.beneficiaryNickname) {
      options.beneficiaryNickname = body.beneficiaryNickname;
    }
    if (body.paymentAddress) {
      options.paymentAddress = body.paymentAddress;
    }
    if (body.toAccount) {
      options.toAccount = body.toAccount;
    }

    // Validate at least one payment destination is provided
    if (!options.beneficiaryId && !options.beneficiaryNickname && !options.paymentAddress && !options.toAccount) {
      return NextResponse.json(
        { error: 'Payment destination required: beneficiaryId, beneficiaryNickname, paymentAddress, or toAccount' },
        { status: 400 }
      );
    }

    // Initiate payment
    const result = await initiatePayment(
      body.userId,
      body.fromAccount,
      options,
      body.amount,
      body.description
    );

    // Return response (include OTP in development mode)
    const isDevelopment = process.env.NODE_ENV === 'development';
    
    return NextResponse.json(
      {
        transaction: result.transaction,
        paymentSessionId: result.paymentSessionId,
        message: 'OTP sent to your registered email/phone',
        ...(isDevelopment && { otpCode: result.otpCode }), // Only in development
      },
      { status: 200 }
    );
  } catch (error) {
    console.error('Error initiating payment:', error);

    if (error instanceof Error) {
      // Handle specific business logic errors
      if (error.message.includes('not found') || error.message.includes('Beneficiary')) {
        return NextResponse.json(
          { error: error.message },
          { status: 404 }
        );
      }
      if (error.message.includes('Insufficient') || error.message.includes('balance')) {
        return NextResponse.json(
          { error: error.message },
          { status: 400 }
        );
      }
      if (error.message.includes('Invalid') || error.message.includes('required')) {
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

