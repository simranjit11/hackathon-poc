/**
 * Elicitation Manager Component
 * ==============================
 * Main component that manages elicitation UI rendering and submission.
 * Routes to appropriate component based on elicitation type.
 */

'use client';

import { useElicitation } from '@/hooks/useElicitation';
import { validateOTP } from '@/lib/elicitation-types';
import { cn } from '@/lib/utils';
import { ConfirmationDialog } from './ConfirmationDialog';
import { ElicitationForm } from './ElicitationForm';
import { OTPInput } from './OTPInput';

/**
 * Elicitation Manager Component
 * ==============================
 * Main component that manages elicitation UI rendering and submission.
 * Routes to appropriate component based on elicitation type.
 */

/**
 * Elicitation Manager Component
 * ==============================
 * Main component that manages elicitation UI rendering and submission.
 * Routes to appropriate component based on elicitation type.
 */

/**
 * Elicitation Manager Component
 * ==============================
 * Main component that manages elicitation UI rendering and submission.
 * Routes to appropriate component based on elicitation type.
 */

export interface ElicitationManagerProps {
  className?: string;
}

export function ElicitationManager({ className }: ElicitationManagerProps) {
  const { active, request, isSubmitting, error, submitResponse, cancel, clearError, isConnected } =
    useElicitation();

  // Don't render if no active elicitation
  if (!active || !request) {
    return null;
  }

  const { schema } = request;

  // Handle OTP submission
  const handleOTPComplete = async (otp: string) => {
    if (!validateOTP(otp)) {
      return;
    }
    await submitResponse({ otp_code: otp });
  };

  // Handle confirmation
  const handleConfirm = async () => {
    await submitResponse({ confirmed: true });
  };

  // Handle form submission
  const handleFormSubmit = async (values: Record<string, any>) => {
    await submitResponse(values);
  };

  // Render appropriate UI based on elicitation type
  const renderElicitationUI = () => {
    switch (schema.elicitation_type) {
      case 'otp':
        return (
          <div className="space-y-6">
            <div className="text-center">
              <h3 className="mb-2 text-lg font-medium text-gray-900">Enter OTP</h3>
              <p className="text-sm text-gray-500">
                To complete this payment of {schema.context.amount} to {schema.context.payee}
              </p>
            </div>

            <OTPInput
              length={6}
              onComplete={handleOTPComplete}
              onCancel={cancel}
              disabled={isSubmitting}
              error={error || undefined}
              autoFocus
            />

            {!isSubmitting && (
              <div className="text-center">
                <button
                  onClick={cancel}
                  className="text-sm text-gray-600 underline hover:text-gray-900"
                >
                  Cancel Transaction
                </button>
              </div>
            )}
          </div>
        );

      case 'confirmation':
        return (
          <ConfirmationDialog
            context={schema.context}
            onConfirm={handleConfirm}
            onCancel={cancel}
            disabled={isSubmitting}
            error={error || undefined}
          />
        );

      case 'form':
      case 'supervisor_approval':
        return (
          <div className="space-y-4">
            <div className="text-center">
              <h3 className="mb-2 text-lg font-medium text-gray-900">
                {schema.elicitation_type === 'supervisor_approval'
                  ? 'Supervisor Approval Required'
                  : 'Additional Information Required'}
              </h3>
              <p className="text-sm text-gray-500">
                Payment: {schema.context.amount} to {schema.context.payee}
              </p>
            </div>

            <ElicitationForm
              fields={schema.fields}
              onSubmit={handleFormSubmit}
              onCancel={cancel}
              disabled={isSubmitting}
              error={error || undefined}
            />
          </div>
        );

      default:
        return (
          <div className="text-center text-gray-500">
            <p>Unknown elicitation type: {schema.elicitation_type}</p>
            <button
              onClick={cancel}
              className="mt-4 text-sm text-blue-600 underline hover:text-blue-800"
            >
              Cancel
            </button>
          </div>
        );
    }
  };

  return (
    <>
      {/* Overlay */}
      <div
        className={cn(
          'bg-opacity-50 fixed inset-0 z-40 bg-black',
          'transition-opacity duration-300',
          active ? 'opacity-100' : 'pointer-events-none opacity-0'
        )}
        onClick={cancel}
      />

      {/* Modal */}
      <div
        className={cn(
          'fixed inset-0 z-50 flex items-center justify-center p-4',
          'pointer-events-none',
          className
        )}
      >
        <div
          className={cn(
            'w-full max-w-lg rounded-lg bg-white p-6 shadow-xl',
            'pointer-events-auto',
            'transform transition-all duration-300',
            active ? 'scale-100 opacity-100' : 'scale-95 opacity-0'
          )}
          onClick={(e) => e.stopPropagation()}
        >
          {/* Connection Status Warning */}
          {!isConnected && (
            <div className="mb-4 rounded-md bg-yellow-50 p-4">
              <div className="flex">
                <div className="flex-shrink-0">
                  <svg
                    className="h-5 w-5 text-yellow-400"
                    xmlns="http://www.w3.org/2000/svg"
                    viewBox="0 0 20 20"
                    fill="currentColor"
                  >
                    <path
                      fillRule="evenodd"
                      d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z"
                      clipRule="evenodd"
                    />
                  </svg>
                </div>
                <div className="ml-3">
                  <p className="text-sm text-yellow-700">Connection lost. Reconnecting...</p>
                </div>
              </div>
            </div>
          )}

          {/* Elicitation Content */}
          {renderElicitationUI()}

          {/* Timeout Indicator */}
          {schema.timeout_seconds && (
            <div className="mt-4 text-center">
              <p className="text-xs text-gray-400">
                This request will expire in {Math.floor(schema.timeout_seconds / 60)} minutes
              </p>
            </div>
          )}
        </div>
      </div>
    </>
  );
}
