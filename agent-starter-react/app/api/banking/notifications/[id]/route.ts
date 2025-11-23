import { NextRequest, NextResponse } from 'next/server';
import { extractTokenFromHeader, validateAccessToken } from '@/lib/auth';
import { corsPreflight, corsResponse } from '@/lib/cors';
import { prisma } from '@/lib/db/prisma';

const VALID_CHANNELS = ['email', 'sms', 'push'];
const VALID_EVENT_TYPES = ['payment', 'alert', 'balance', 'transaction'];

/**
 * PUT /api/banking/notifications/[id]
 * Update an existing notification preference
 */
export async function PUT(request: NextRequest, { params }: { params: Promise<{ id: string }> }) {
  if (request.method === 'OPTIONS') {
    return corsPreflight();
  }

  try {
    const authHeader = request.headers.get('Authorization');
    const token = extractTokenFromHeader(authHeader);
    const user = await validateAccessToken(token);

    const { id } = await params;
    const body = await request.json();

    // Verify preference belongs to user
    const existingPreference = await prisma.notificationPreference.findFirst({
      where: {
        id,
        userId: user.user_id,
      },
    });

    if (!existingPreference) {
      return corsResponse({ error: 'Notification preference not found' }, 404);
    }

    // Validate channel if provided
    if (body.channel && !VALID_CHANNELS.includes(body.channel)) {
      return corsResponse({ error: `channel must be one of: ${VALID_CHANNELS.join(', ')}` }, 400);
    }

    // Validate eventType if provided
    if (body.eventType && !VALID_EVENT_TYPES.includes(body.eventType)) {
      return corsResponse(
        { error: `eventType must be one of: ${VALID_EVENT_TYPES.join(', ')}` },
        400
      );
    }

    // Check unique constraint if channel or eventType changed
    const channel = body.channel || existingPreference.channel;
    const eventType = body.eventType || existingPreference.eventType;

    if (body.channel || body.eventType) {
      const conflicting = await prisma.notificationPreference.findUnique({
        where: {
          userId_channel_eventType: {
            userId: user.user_id,
            channel,
            eventType,
          },
        },
      });

      if (conflicting && conflicting.id !== id) {
        return corsResponse(
          { error: 'Notification preference already exists for this channel and event type' },
          409
        );
      }
    }

    // Update preference
    const updatedPreference = await prisma.notificationPreference.update({
      where: { id },
      data: {
        channel: body.channel,
        eventType: body.eventType,
        isEnabled: body.isEnabled !== undefined ? body.isEnabled : undefined,
      },
    });

    return corsResponse(
      {
        data: {
          id: updatedPreference.id,
          channel: updatedPreference.channel,
          eventType: updatedPreference.eventType,
          isEnabled: updatedPreference.isEnabled,
          createdAt: updatedPreference.createdAt.toISOString(),
          updatedAt: updatedPreference.updatedAt.toISOString(),
        },
      },
      200
    );
  } catch (error: any) {
    console.error('Error updating notification preference:', error);

    if (error instanceof Error && error.message.includes('missing')) {
      return corsResponse({ error: 'Authorization header is required' }, 401);
    }

    if (
      error instanceof Error &&
      (error.message.includes('Invalid') || error.message.includes('expired'))
    ) {
      return corsResponse({ error: error.message }, 401);
    }

    // Handle Prisma unique constraint error
    if (error.code === 'P2002') {
      return corsResponse(
        { error: 'Notification preference already exists for this channel and event type' },
        409
      );
    }

    return corsResponse({ error: 'Internal server error' }, 500);
  }
}

/**
 * DELETE /api/banking/notifications/[id]
 * Delete a notification preference
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

    // Verify preference belongs to user
    const preference = await prisma.notificationPreference.findFirst({
      where: {
        id,
        userId: user.user_id,
      },
    });

    if (!preference) {
      return corsResponse({ error: 'Notification preference not found' }, 404);
    }

    // Delete preference
    await prisma.notificationPreference.delete({
      where: { id },
    });

    return new NextResponse(null, { status: 204 });
  } catch (error) {
    console.error('Error deleting notification preference:', error);

    if (error instanceof Error && error.message.includes('missing')) {
      return corsResponse({ error: 'Authorization header is required' }, 401);
    }

    if (
      error instanceof Error &&
      (error.message.includes('Invalid') || error.message.includes('expired'))
    ) {
      return corsResponse({ error: error.message }, 401);
    }

    return corsResponse({ error: 'Internal server error' }, 500);
  }
}

export async function OPTIONS() {
  return corsPreflight();
}
