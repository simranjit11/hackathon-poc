/**
 * Elicitation Cancellation Endpoint
 * ==================================
 * Handles cancelling an active elicitation request.
 */
import { NextRequest, NextResponse } from 'next/server';
import { z } from 'zod';

// Validation schema
const CancelRequestSchema = z.object({
  reason: z.string().optional().default('Cancelled by user'),
});

export async function POST(request: NextRequest, { params }: { params: Promise<{ id: string }> }) {
  try {
    const { id: elicitationId } = await params;

    // Validate UUID format
    const uuidRegex = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
    if (!uuidRegex.test(elicitationId)) {
      return NextResponse.json({ error: 'Invalid elicitation ID format' }, { status: 400 });
    }

    // Parse request body
    const body = await request.json();
    const validated = CancelRequestSchema.safeParse(body);

    if (!validated.success) {
      return NextResponse.json(
        { error: 'Invalid request format', details: validated.error.issues },
        { status: 400 }
      );
    }

    const { reason } = validated.data;

    console.log(`[Elicitation] Cancel request for ${elicitationId}: ${reason}`);

    // In production, this would:
    // 1. Verify elicitation exists in Redis
    // 2. Check user owns the elicitation (from JWT)
    // 3. Update status to cancelled in Redis
    // 4. Remove from queue
    // 5. Notify client via LiveKit data channel

    // Mock implementation
    console.log(`[Elicitation] Cancelled ${elicitationId}`);

    return NextResponse.json({
      status: 'cancelled',
      elicitation_id: elicitationId,
      reason,
    });
  } catch (error) {
    console.error('[Elicitation] Error cancelling:', error);
    return NextResponse.json(
      {
        error: error instanceof Error ? error.message : 'Failed to cancel elicitation',
      },
      { status: 500 }
    );
  }
}
