/**
 * LiveKit Data Channel Hook
 * ==========================
 * Hook for handling data channel messages including elicitation requests.
 */
import { useCallback, useEffect, useRef } from 'react';
import { DataPacket_Kind, RoomEvent } from 'livekit-client';
import { useRoomContext } from '@livekit/components-react';
import type { ElicitationMessage } from '@/lib/elicitation-types';

export interface DataChannelMessage {
  type: string;
  payload: any;
  timestamp: number;
}

export interface UseDataChannelOptions {
  onElicitationReceived?: (message: ElicitationMessage) => void;
  onMessage?: (message: DataChannelMessage) => void;
}

export function useDataChannel(options: UseDataChannelOptions = {}) {
  const room = useRoomContext();
  const { onElicitationReceived, onMessage } = options;

  // Use refs to avoid recreating callbacks on every render
  const onElicitationRef = useRef(onElicitationReceived);
  const onMessageRef = useRef(onMessage);

  useEffect(() => {
    onElicitationRef.current = onElicitationReceived;
    onMessageRef.current = onMessage;
  }, [onElicitationReceived, onMessage]);

  // Handle incoming data channel messages
  useEffect(() => {
    if (!room) return;

    const handleDataReceived = (payload: Uint8Array, participant?: any, kind?: DataPacket_Kind) => {
      try {
        // Decode the data
        const decoder = new TextDecoder();
        const text = decoder.decode(payload);
        const data = JSON.parse(text);

        console.log('[DataChannel] Received message:', data);

        // Create message object
        const message: DataChannelMessage = {
          type: data.type || 'unknown',
          payload: data,
          timestamp: Date.now(),
        };

        // Call general message handler
        if (onMessageRef.current) {
          onMessageRef.current(message);
        }

        // Handle elicitation messages
        if (
          data.type === 'elicitation' ||
          data.type === 'elicitation_cancelled' ||
          data.type === 'elicitation_expired'
        ) {
          if (onElicitationRef.current) {
            onElicitationRef.current(data as ElicitationMessage);
          }
        }
      } catch (error) {
        console.error('[DataChannel] Error parsing message:', error);
      }
    };

    room.on(RoomEvent.DataReceived, handleDataReceived);

    return () => {
      room.off(RoomEvent.DataReceived, handleDataReceived);
    };
  }, [room]);

  // Send data via data channel
  const sendData = useCallback(
    async (data: any) => {
      if (!room || !room.localParticipant) {
        console.error('[DataChannel] Room not connected');
        return false;
      }

      try {
        const encoder = new TextEncoder();
        const payload = encoder.encode(JSON.stringify(data));

        await room.localParticipant.publishData(payload, { reliable: true });

        console.log('[DataChannel] Sent message:', data);
        return true;
      } catch (error) {
        console.error('[DataChannel] Error sending data:', error);
        return false;
      }
    },
    [room]
  );

  return {
    sendData,
    isConnected: !!room && room.state === 'connected',
  };
}
