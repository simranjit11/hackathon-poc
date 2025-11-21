/**
 * Confirmation Dialog Component
 * ==============================
 * Displays payment details and confirmation/cancel buttons.
 */

'use client';

import { useState } from 'react';
import type { ElicitationContext } from '@/lib/elicitation-types';
import { cn } from '@/lib/utils';

export interface ConfirmationDialogProps {
  context: ElicitationContext;
  onConfirm: () => void;
  onCancel: () => void;
  disabled?: boolean;
  error?: string;
}

export function ConfirmationDialog({
  context,
  onConfirm,
  onCancel,
  disabled = false,
  error,
}: ConfirmationDialogProps) {
  const [isConfirming, setIsConfirming] = useState(false);

  const handleConfirm = async () => {
    setIsConfirming(true);
    try {
      await onConfirm();
    } finally {
      setIsConfirming(false);
    }
  };

  return (
    <div className="flex flex-col space-y-6 max-w-md mx-auto">
      {/* Header */}
      <div className="text-center">
        <div className="mx-auto flex items-center justify-center h-12 w-12 rounded-full bg-yellow-100 mb-4">
          <svg
            className="h-6 w-6 text-yellow-600"
            xmlns="http://www.w3.org/2000/svg"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
            />
          </svg>
        </div>
        <h3 className="text-lg font-medium text-gray-900">Confirm Payment</h3>
        <p className="mt-2 text-sm text-gray-500">
          Please review and confirm the payment details below
        </p>
      </div>

      {/* Payment Details */}
      <div className="bg-gray-50 rounded-lg p-4 space-y-3">
        <div className="flex justify-between items-center">
          <span className="text-sm font-medium text-gray-500">Amount</span>
          <span className="text-lg font-semibold text-gray-900">
            {context.amount}
          </span>
        </div>

        <div className="border-t border-gray-200" />

        <div className="flex justify-between items-center">
          <span className="text-sm font-medium text-gray-500">To</span>
          <span className="text-sm font-medium text-gray-900">
            {context.payee}
          </span>
        </div>

        <div className="flex justify-between items-center">
          <span className="text-sm font-medium text-gray-500">From Account</span>
          <span className="text-sm text-gray-900">{context.account}</span>
        </div>

        {context.description && (
          <>
            <div className="border-t border-gray-200" />
            <div className="flex justify-between items-start">
              <span className="text-sm font-medium text-gray-500">Description</span>
              <span className="text-sm text-gray-900 text-right max-w-[60%]">
                {context.description}
              </span>
            </div>
          </>
        )}

        {context.additional_info && Object.keys(context.additional_info).length > 0 && (
          <>
            <div className="border-t border-gray-200" />
            {Object.entries(context.additional_info).map(([key, value]) => (
              <div key={key} className="flex justify-between items-center">
                <span className="text-sm font-medium text-gray-500 capitalize">
                  {key.replace(/_/g, ' ')}
                </span>
                <span className="text-sm text-gray-900">{String(value)}</span>
              </div>
            ))}
          </>
        )}
      </div>

      {/* Error Message */}
      {error && (
        <div className="rounded-md bg-red-50 p-4">
          <div className="flex">
            <div className="flex-shrink-0">
              <svg
                className="h-5 w-5 text-red-400"
                xmlns="http://www.w3.org/2000/svg"
                viewBox="0 0 20 20"
                fill="currentColor"
              >
                <path
                  fillRule="evenodd"
                  d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z"
                  clipRule="evenodd"
                />
              </svg>
            </div>
            <div className="ml-3">
              <p className="text-sm text-red-700">{error}</p>
            </div>
          </div>
        </div>
      )}

      {/* Action Buttons */}
      <div className="flex space-x-3">
        <button
          onClick={onCancel}
          disabled={disabled || isConfirming}
          className={cn(
            'flex-1 px-4 py-2 border border-gray-300 rounded-lg',
            'text-sm font-medium text-gray-700 bg-white',
            'hover:bg-gray-50 focus:outline-none focus:ring-2',
            'focus:ring-offset-2 focus:ring-gray-500',
            'transition-colors duration-200',
            (disabled || isConfirming) && 'opacity-50 cursor-not-allowed'
          )}
        >
          Cancel
        </button>

        <button
          onClick={handleConfirm}
          disabled={disabled || isConfirming}
          className={cn(
            'flex-1 px-4 py-2 border border-transparent rounded-lg',
            'text-sm font-medium text-white bg-blue-600',
            'hover:bg-blue-700 focus:outline-none focus:ring-2',
            'focus:ring-offset-2 focus:ring-blue-500',
            'transition-colors duration-200',
            (disabled || isConfirming) && 'opacity-50 cursor-not-allowed'
          )}
        >
          {isConfirming ? (
            <span className="flex items-center justify-center">
              <svg
                className="animate-spin -ml-1 mr-2 h-4 w-4 text-white"
                xmlns="http://www.w3.org/2000/svg"
                fill="none"
                viewBox="0 0 24 24"
              >
                <circle
                  className="opacity-25"
                  cx="12"
                  cy="12"
                  r="10"
                  stroke="currentColor"
                  strokeWidth="4"
                />
                <path
                  className="opacity-75"
                  fill="currentColor"
                  d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                />
              </svg>
              Confirming...
            </span>
          ) : (
            'Confirm Payment'
          )}
        </button>
      </div>

      {/* Security Notice */}
      <p className="text-xs text-center text-gray-400">
        🔒 This transaction is secure and encrypted
      </p>
    </div>
  );
}

