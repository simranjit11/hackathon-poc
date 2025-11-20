/**
 * Elicitation Management Hook
 * ============================
 * Manages elicitation state and UI rendering.
 */

import { useState, useCallback, useEffect } from 'react';
import { useDataChannel } from './useDataChannel';
import type {
  ElicitationRequest,
  ElicitationResponse,
  ElicitationMessage,
  isElicitationRequest,
  isElicitationCancellation,
  isElicitationExpiration,
} from '@/lib/elicitation-types';

export interface ElicitationState {
  active: boolean;
  request: ElicitationRequest | null;
  isSubmitting: boolean;
  error: string | null;
}

export function useElicitation() {
  const [state, setState] = useState<ElicitationState>({
    active: false,
    request: null,
    isSubmitting: false,
    error: null,
  });

  // Handle incoming elicitation messages
  const handleElicitationMessage = useCallback((message: ElicitationMessage) => {
    console.log('[Elicitation] Received message:', message);

    if (isElicitationRequest(message)) {
      // New elicitation request
      setState({
        active: true,
        request: message,
        isSubmitting: false,
        error: null,
      });
    } else if (isElicitationCancellation(message)) {
      // Elicitation cancelled
      setState({
        active: false,
        request: null,
        isSubmitting: false,
        error: null,
      });
    } else if (isElicitationExpiration(message)) {
      // Elicitation expired
      setState({
        active: false,
        request: null,
        isSubmitting: false,
        error: message.message || 'Elicitation has expired',
      });
    }
  }, []);

  const { sendData, isConnected } = useDataChannel({
    onElicitationReceived: handleElicitationMessage,
  });

  // Submit elicitation response
  const submitResponse = useCallback(
    async (userInput: Record<string, any>, biometric_token?: string) => {
      if (!state.request) {
        console.error('[Elicitation] No active request to respond to');
        return false;
      }

      if (!isConnected) {
        console.error('[Elicitation] Not connected to data channel');
        setState(prev => ({ ...prev, error: 'Not connected. Please try again.' }));
        return false;
      }

      setState(prev => ({ ...prev, isSubmitting: true, error: null }));

      try {
        const response: ElicitationResponse = {
          type: 'elicitation_response',
          elicitation_id: state.request.elicitation_id,
          user_input: userInput,
          biometric_token,
          timestamp: new Date().toISOString(),
        };

        console.log('[Elicitation] Submitting response:', response);

        const success = await sendData(response);

        if (success) {
          // Clear the elicitation after successful submission
          setState({
            active: false,
            request: null,
            isSubmitting: false,
            error: null,
          });
          return true;
        } else {
          setState(prev => ({
            ...prev,
            isSubmitting: false,
            error: 'Failed to send response. Please try again.',
          }));
          return false;
        }
      } catch (error) {
        console.error('[Elicitation] Error submitting response:', error);
        setState(prev => ({
          ...prev,
          isSubmitting: false,
          error: error instanceof Error ? error.message : 'Failed to submit response',
        }));
        return false;
      }
    },
    [state.request, isConnected, sendData]
  );

  // Cancel elicitation
  const cancel = useCallback(() => {
    setState({
      active: false,
      request: null,
      isSubmitting: false,
      error: null,
    });
  }, []);

  // Clear error
  const clearError = useCallback(() => {
    setState(prev => ({ ...prev, error: null }));
  }, []);

  return {
    ...state,
    submitResponse,
    cancel,
    clearError,
    isConnected,
  };
}

