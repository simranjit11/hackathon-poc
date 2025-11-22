/**
 * Elicitation Resume Endpoint
 * ============================
 * Handles resuming payment execution after user provides elicitation response (OTP/confirmation).
 * 
 * This endpoint receives the OTP from the frontend and calls the MCP server's
 * confirm_payment tool to complete the transaction.
 */

import { NextRequest, NextResponse } from 'next/server';
import { z } from 'zod';
import { confirmPayment } from '@/lib/banking/payments';
import { getJWTForUser } from '@/lib/auth/jwt';

// Validation schemas
const ResumePaymentSchema = z.object({
    elicitation_id: z.string().uuid(),
    tool_call_id: z.string(),
    user_input: z.record(z.any()),
    biometric_token: z.string().optional(),
    suspended_arguments: z.object({
        user_id: z.string(),
        from_account: z.string(),
        to_account: z.string(),
        amount: z.number(),
        description: z.string().optional(),
        payment_session_id: z.string().optional(),
    }),
});

/**
 * Validate OTP code (mock validation)
 */
function validateOTP(otpCode: string): { valid: boolean; error?: string } {
    // Mock validation - in production, verify with actual OTP service
    // For testing, accept "123456" as valid OTP
    if (otpCode === "123456") {
        return { valid: true };
    }
    return { valid: false, error: "Invalid OTP code. Please try again." };
}

/**
 * Validate confirmation response
 */
function validateConfirmation(confirmed: boolean): { valid: boolean; error?: string } {
    if (confirmed) {
        return { valid: true };
    }
    return { valid: false, error: "Payment confirmation denied" };
}

/**
 * Validate elicitation response based on type
 */
function validateElicitationResponse(
    userInput: Record<string, any>,
    elicitationType: string
): { valid: boolean; error?: string } {
    switch (elicitationType) {
        case "otp":
            return validateOTP(userInput.otp_code || "");
        case "confirmation":
            return validateConfirmation(userInput.confirmed || false);
        case "supervisor_approval":
            if (userInput.supervisor_id && userInput.approval_code) {
                return { valid: true };
            }
            return { valid: false, error: "Invalid supervisor approval" };
        default:
            return { valid: false, error: "Unknown elicitation type" };
    }
}

/**
 * Complete payment after successful elicitation (mock implementation)
 */
function completePayment(suspendedArgs: any) {
    const confirmationNumber = `TXN${Math.random().toString(36).substring(2, 14).toUpperCase()}`;

    return {
        status: "completed",
        confirmation_number: confirmationNumber,
        from_account: suspendedArgs.from_account,
        to_account: suspendedArgs.to_account,
        amount: suspendedArgs.amount,
        description: suspendedArgs.description || "",
        timestamp: new Date().toISOString(),
        message: "Payment processed successfully",
    };
}

export async function POST(request: NextRequest) {
    try {
        // Parse request body
        const body = await request.json();

        // Validate request
        const validated = ResumePaymentSchema.safeParse(body);
        if (!validated.success) {
            return NextResponse.json(
                {
                    status: "failed",
                    error: "Invalid request format",
                    details: validated.error.errors
                },
                { status: 400 }
            );
        }

        const { elicitation_id, tool_call_id, user_input, suspended_arguments } = validated.data;

        console.log(`[Elicitation] Resume payment request for ${elicitation_id}`);

        // Determine elicitation type based on amount
        const amount = suspended_arguments.amount;
        const elicitationType = amount >= 1000.0 ? "otp" : "confirmation";

        // Validate user input
        const validation = validateElicitationResponse(user_input, elicitationType);

        if (!validation.valid) {
            console.warn(`[Elicitation] Invalid response: ${validation.error}`);
            return NextResponse.json({
                status: "failed",
                error: validation.error,
            });
        }

        // Complete payment (mock implementation)
        const paymentResult = completePayment(suspended_arguments);

        console.log(
            `[Elicitation] Payment completed: confirmation=${paymentResult.confirmation_number}`
        );

        return NextResponse.json({
            status: "completed",
            payment_result: paymentResult,
        });

    } catch (error) {
        console.error("[Elicitation] Error resuming payment:", error);
        return NextResponse.json(
            {
                status: "failed",
                error: error instanceof Error ? error.message : "Failed to process payment",
            },
            { status: 500 }
        );
    }
}

