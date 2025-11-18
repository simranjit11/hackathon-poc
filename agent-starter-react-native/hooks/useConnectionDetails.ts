import { useEffect, useState } from 'react';
import { getAccessToken } from '@/lib/auth';

// TODO: Add your Sandbox ID here
const sandboxID = '';
const tokenEndpoint =
  'https://cloud-api.livekit.io/api/sandbox/connection-details';

// For use without a token server.
const hardcodedUrl = '';
const hardcodedToken = '';

/**
 * Retrieves a LiveKit token.
 *
 * Currently configured to use LiveKit's Sandbox token server.
 * When building an app for production, you should use your own token server.
 */
export function useConnectionDetails(): ConnectionDetails | undefined {
  const [details, setDetails] = useState<ConnectionDetails | undefined>(() => {
    return undefined;
  });

  useEffect(() => {
    fetchToken().then(details => {
      setDetails(details);
    });
  }, []);

  return details;
}

export async function fetchToken() : Promise<ConnectionDetails | undefined> {
    // For sandbox mode
    if (sandboxID) {
      const response = await fetch(tokenEndpoint, {
        headers: { 'X-Sandbox-ID': sandboxID },
      });
      const json = await response.json();

      if (json.serverUrl && json.participantToken) {
        return {
          url: json.serverUrl,
          token: json.participantToken,
        };
      } else {
        return undefined;
      }
    }

    // For production mode with custom token server
    // Get access token for authentication
    const accessToken = await getAccessToken();
    const connectionDetailsEndpoint = process.env.EXPO_PUBLIC_CONN_DETAILS_ENDPOINT || '/api/connection-details';
    
    const headers: HeadersInit = {
      'Content-Type': 'application/json',
    };

    // Add Authorization header if access token is available
    if (accessToken) {
      headers['Authorization'] = `Bearer ${accessToken}`;
    }

    try {
      const response = await fetch(connectionDetailsEndpoint, {
        method: 'POST',
        headers,
        body: JSON.stringify({
          room_config: {
            agents: [{ agent_name: 'banking-assistant' }],
          },
        }),
      });

      // Handle authentication errors
      if (response.status === 401) {
        const errorText = await response.text();
        throw new Error(`Authentication failed: ${errorText}`);
      }

      if (!response.ok) {
        const errorText = await response.text();
        throw new Error(`Failed to fetch connection details: ${errorText}`);
      }

      const json = await response.json();

      if (json.serverUrl && json.participantToken) {
        return {
          url: json.serverUrl,
          token: json.participantToken,
        };
      } else {
        return undefined;
      }
    } catch (error) {
      console.error('Error fetching connection details:', error);
      // Fallback to hardcoded values if available
      if (hardcodedUrl && hardcodedToken) {
        return {
          url: hardcodedUrl,
          token: hardcodedToken,
        };
      }
      return undefined;
    }
}

export type ConnectionDetails = {
  url: string;
  token: string;
};
