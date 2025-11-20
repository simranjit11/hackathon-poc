import { NextRequest } from 'next/server';
import { validateAccessToken, extractTokenFromHeader } from '@/lib/auth';
import { corsResponse, corsPreflight } from '@/lib/cors';
import { prisma } from '@/lib/db/prisma';

const VALID_CHANNELS = ['email', 'sms', 'push'];
const VALID_EVENT_TYPES = ['payment', 'alert', 'balance', 'transaction'];

/**
 * GET /api/banking/notifications
 * Retrieve all notification preferences for authenticated user
 */
export async function GET(request: NextRequest) {
  if (request.method === 'OPTIONS') {
    return corsPreflight();
  }

  try {
    const authHeader = request.headers.get('Authorization');
    const token = extractTokenFromHeader(authHeader);
    const user = await validateAccessToken(token);

    const preferences = await prisma.notificationPreference.findMany({
      where: { userId: user.user_id },
      select: {
        id: true,
        channel: true,
        eventType: true,
        isEnabled: true,
        createdAt: true,
        updatedAt: true,
      },
      orderBy: [{ channel: 'asc' }, { eventType: 'asc' }],
    });

    return corsResponse(
      {
        data: preferences.map((pref) => ({
          id: pref.id,
          channel: pref.channel,
          eventType: pref.eventType,
          isEnabled: pref.isEnabled,
          createdAt: pref.createdAt.toISOString(),
          updatedAt: pref.updatedAt.toISOString(),
        })),
      },
      200
    );
  } catch (error) {
    console.error('Error fetching notification preferences:', error);

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
 * POST /api/banking/notifications
 * Create a new notification preference
 */
export async function POST(request: NextRequest) {
  if (request.method === 'OPTIONS') {
    return corsPreflight();
  }

  try {
    const authHeader = request.headers.get('Authorization');
    const token = extractTokenFromHeader(authHeader);
    const user = await validateAccessToken(token);

    const body = await request.json();
    const { channel, eventType, isEnabled } = body;

    // Validate required fields
    if (!channel || !eventType) {
      return corsResponse(
        { error: 'channel and eventType are required' },
        400
      );
    }

    // Validate channel
    if (!VALID_CHANNELS.includes(channel)) {
      return corsResponse(
        { error: `channel must be one of: ${VALID_CHANNELS.join(', ')}` },
        400
      );
    }

    // Validate eventType
    if (!VALID_EVENT_TYPES.includes(eventType)) {
      return corsResponse(
        { error: `eventType must be one of: ${VALID_EVENT_TYPES.join(', ')}` },
        400
      );
    }

    // Check for existing preference (unique constraint)
    const existing = await prisma.notificationPreference.findUnique({
      where: {
        userId_channel_eventType: {
          userId: user.user_id,
          channel,
          eventType,
        },
      },
    });

    if (existing) {
      return corsResponse(
        { error: 'Notification preference already exists for this channel and event type' },
        409
      );
    }

    // Create preference
    const preference = await prisma.notificationPreference.create({
      data: {
        userId: user.user_id,
        channel,
        eventType,
        isEnabled: isEnabled !== undefined ? isEnabled : true,
      },
    });

    return corsResponse(
      {
        data: {
          id: preference.id,
          channel: preference.channel,
          eventType: preference.eventType,
          isEnabled: preference.isEnabled,
          createdAt: preference.createdAt.toISOString(),
          updatedAt: preference.updatedAt.toISOString(),
        },
      },
      201
    );
  } catch (error: any) {
    console.error('Error creating notification preference:', error);

    if (error instanceof Error && error.message.includes('missing')) {
      return corsResponse({ error: 'Authorization header is required' }, 401);
    }

    if (error instanceof Error && (error.message.includes('Invalid') || error.message.includes('expired'))) {
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

export async function OPTIONS() {
  return corsPreflight();
}


