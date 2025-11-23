import { NextRequest, NextResponse } from 'next/server';
import { PaymentInitiationOptions, initiatePayment } from '@/lib/banking/payments';
import { createLatencyLogger } from '@/lib/api-latency-logger';

const latencyLogger = createLatencyLogger('/api/internal/banking/payments/initiate', 'POST');

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
  const startTime = latencyLogger.start();
  
  const apiKey = request.headers.get('x-api-key');

  if (apiKey !== process.env.INTERNAL_API_KEY) {
    latencyLogger.end(startTime, 401);
    return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
  }

  try {
    // Parse request body
    const body: PaymentInitiateRequest = await request.json();

    // Validate required fields
    if (!body.userId || !body.fromAccount || !body.amount) {
      latencyLogger.end(startTime, 400, undefined, {
        missing_fields: {
          userId: !body.userId,
          fromAccount: !body.fromAccount,
          amount: !body.amount,
        },
      });
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
    if (
      !options.beneficiaryId &&
      !options.beneficiaryNickname &&
      !options.paymentAddress &&
      !options.toAccount
    ) {
      latencyLogger.end(startTime, 400, undefined, {
        error: 'Payment destination required',
      });
      return NextResponse.json(
        {
          error:
            'Payment destination required: beneficiaryId, beneficiaryNickname, paymentAddress, or toAccount',
        },
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

    latencyLogger.end(startTime, 200, undefined, {
      paymentSessionId: result.paymentSessionId,
      amount: body.amount,
    });

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

    let statusCode = 500;
    if (error instanceof Error) {
      // Handle specific business logic errors
      if (error.message.includes('not found') || error.message.includes('Beneficiary')) {
        statusCode = 404;
        latencyLogger.end(startTime, statusCode, error);
        return NextResponse.json({ error: error.message }, { status: statusCode });
      }
      if (error.message.includes('Insufficient') || error.message.includes('balance')) {
        statusCode = 400;
        latencyLogger.end(startTime, statusCode, error);
        return NextResponse.json({ error: error.message }, { status: statusCode });
      }
      if (error.message.includes('Invalid') || error.message.includes('required')) {
        statusCode = 400;
        latencyLogger.end(startTime, statusCode, error);
        return NextResponse.json({ error: error.message }, { status: statusCode });
      }
    }

    latencyLogger.end(startTime, statusCode, error instanceof Error ? error : new Error(String(error)));
    return NextResponse.json({ error: 'Internal server error' }, { status: statusCode });
  }
}
