import { NextResponse } from 'next/server';
import { AccessToken, type AccessTokenOptions, type VideoGrant } from 'livekit-server-sdk';
import { RoomConfiguration } from '@livekit/protocol';
import { type UserIdentity, extractTokenFromHeader, validateAccessToken } from '@/lib/auth';

type ConnectionDetails = {
  serverUrl: string;
  roomName: string;
  participantName: string;
  participantToken: string;
};

// NOTE: you are expected to define the following environment variables in `.env.local`:
const API_KEY = process.env.LIVEKIT_API_KEY;
const API_SECRET = process.env.LIVEKIT_API_SECRET;
const LIVEKIT_URL = process.env.LIVEKIT_URL;

// don't cache the results
export const revalidate = 0;

export async function POST(req: Request) {
  try {
    if (LIVEKIT_URL === undefined) {
      throw new Error('LIVEKIT_URL is not defined');
    }
    if (API_KEY === undefined) {
      throw new Error('LIVEKIT_API_KEY is not defined');
    }
    if (API_SECRET === undefined) {
      throw new Error('LIVEKIT_API_SECRET is not defined');
    }

    // Extract and validate access token from Authorization header
    const authHeader = req.headers.get('Authorization');
    let userIdentity: UserIdentity;

    try {
      const token = extractTokenFromHeader(authHeader);
      userIdentity = await validateAccessToken(token);
    } catch (authError) {
      console.error('Authentication error:', authError);
      return new NextResponse(
        authError instanceof Error ? authError.message : 'Authentication failed',
        { status: 401 }
      );
    }

    // Parse agent configuration from request body
    const body = await req.json();
    const agentName: string = body?.room_config?.agents?.[0]?.agent_name;

    // Generate participant token with user identity
    const participantName = 'user';
    const participantIdentity = `voice_assistant_user_${userIdentity.user_id}`;
    const roomName = `voice_assistant_room_${Date.now()}_${Math.random().toString(36).substring(2, 9)}`;

    const participantToken = await createParticipantToken(
      { identity: participantIdentity, name: participantName },
      roomName,
      agentName,
      userIdentity
    );

    // Return connection details
    const data: ConnectionDetails = {
      serverUrl: LIVEKIT_URL,
      roomName,
      participantToken: participantToken,
      participantName,
    };
    const headers = new Headers({
      'Cache-Control': 'no-store',
    });
    return NextResponse.json(data, { headers });
  } catch (error) {
    if (error instanceof Error) {
      console.error(error);
      return new NextResponse(error.message, { status: 500 });
    }
    return new NextResponse('Internal server error', { status: 500 });
  }
}

function createParticipantToken(
  userInfo: AccessTokenOptions,
  roomName: string,
  agentName?: string,
  userIdentity?: UserIdentity
): Promise<string> {
  const at = new AccessToken(API_KEY, API_SECRET, {
    ...userInfo,
    ttl: '1h', // Set token expiration to 1 hour as per requirements
  });

  const grant: VideoGrant = {
    room: roomName,
    roomJoin: true,
    canPublish: true,
    canPublishData: true,
    canSubscribe: true,
  };
  at.addGrant(grant);

  // Add custom claims to the token metadata
  if (userIdentity) {
    at.metadata = JSON.stringify({
      user_id: userIdentity.user_id,
      email: userIdentity.email,
      roles: userIdentity.roles,
      permissions: userIdentity.permissions,
      session_type: 'voice_assistant',
    });
  }

  if (agentName) {
    at.roomConfig = new RoomConfiguration({
      agents: [{ agentName }],
    });
  }

  return at.toJwt();
}
