import { NextRequest } from 'next/server';
import { validateAccessToken, extractTokenFromHeader } from '@/lib/auth';
import { corsResponse, corsPreflight } from '@/lib/cors';
import { initiatePayment, PaymentInitiationOptions } from '@/lib/banking/payments';

interface PaymentInitiateRequest {
  fromAccount: string; // Account ID or account number
  beneficiaryId?: string;
  beneficiaryNickname?: string;
  paymentAddress?: string;
  toAccount?: string;
  amount: number;
  description?: string;
}

/**
 * POST /api/banking/payments/initiate
 * Initiate a payment and generate OTP for confirmation
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
    const body: PaymentInitiateRequest = await request.json();

    // Validate required fields
    if (!body.fromAccount || !body.amount) {
      return corsResponse(
        { error: 'fromAccount and amount are required' },
        400
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
      return corsResponse(
        { error: 'Payment destination required: beneficiaryId, beneficiaryNickname, paymentAddress, or toAccount' },
        400
      );
    }

    // Initiate payment
    const result = await initiatePayment(
      user.user_id,
      body.fromAccount,
      options,
      body.amount,
      body.description
    );

    // Return response (include OTP in development mode)
    const isDevelopment = process.env.NODE_ENV === 'development';
    
    return corsResponse(
      {
        transaction: result.transaction,
        paymentSessionId: result.paymentSessionId,
        message: 'OTP sent to your registered email/phone',
        ...(isDevelopment && { otpCode: result.otpCode }), // Only in development
      },
      200
    );
  } catch (error) {
    console.error('Error initiating payment:', error);

    if (error instanceof Error && error.message.includes('missing')) {
      return corsResponse(
        { error: 'Authorization header is required' },
        401
      );
    }

    if (error instanceof Error && (error.message.includes('Invalid') || error.message.includes('expired'))) {
      return corsResponse(
        { error: error.message },
        401
      );
    }

    if (error instanceof Error) {
      // Handle specific business logic errors
      if (error.message.includes('not found') || error.message.includes('Beneficiary')) {
        return corsResponse(
          { error: error.message },
          404
        );
      }
      if (error.message.includes('Insufficient') || error.message.includes('balance')) {
        return corsResponse(
          { error: error.message },
          400
        );
      }
      if (error.message.includes('Invalid') || error.message.includes('required')) {
        return corsResponse(
          { error: error.message },
          400
        );
      }
    }

    return corsResponse(
      { error: 'Internal server error' },
      500
    );
  }
}

/**
 * Handle OPTIONS request for CORS preflight
 */
export async function OPTIONS() {
  return corsPreflight();
}


