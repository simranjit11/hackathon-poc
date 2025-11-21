/**
 * OTP Input Component
 * ===================
 * 6-digit OTP input with auto-focus and validation.
 */

'use client';

import { useState, useRef, useEffect, KeyboardEvent, ClipboardEvent } from 'react';
import { cn } from '@/lib/utils';

export interface OTPInputProps {
  length?: number;
  onComplete: (otp: string) => void;
  onCancel?: () => void;
  disabled?: boolean;
  error?: string;
  autoFocus?: boolean;
}

export function OTPInput({
  length = 6,
  onComplete,
  onCancel,
  disabled = false,
  error,
  autoFocus = true,
}: OTPInputProps) {
  const [otp, setOtp] = useState<string[]>(Array(length).fill(''));
  const inputRefs = useRef<(HTMLInputElement | null)[]>([]);

  // Auto-focus first input
  useEffect(() => {
    if (autoFocus && inputRefs.current[0]) {
      inputRefs.current[0]?.focus();
    }
  }, [autoFocus]);

  // Call onComplete when OTP is filled
  useEffect(() => {
    const isComplete = otp.every(digit => digit !== '');
    if (isComplete) {
      onComplete(otp.join(''));
    }
  }, [otp, onComplete]);

  const handleChange = (index: number, value: string) => {
    // Only allow digits
    if (value && !/^\d$/.test(value)) {
      return;
    }

    const newOtp = [...otp];
    newOtp[index] = value;
    setOtp(newOtp);

    // Move to next input if value entered
    if (value && index < length - 1) {
      inputRefs.current[index + 1]?.focus();
    }
  };

  const handleKeyDown = (index: number, e: KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Backspace') {
      e.preventDefault();
      const newOtp = [...otp];
      
      if (otp[index]) {
        // Clear current input
        newOtp[index] = '';
        setOtp(newOtp);
      } else if (index > 0) {
        // Move to previous input and clear it
        newOtp[index - 1] = '';
        setOtp(newOtp);
        inputRefs.current[index - 1]?.focus();
      }
    } else if (e.key === 'ArrowLeft' && index > 0) {
      e.preventDefault();
      inputRefs.current[index - 1]?.focus();
    } else if (e.key === 'ArrowRight' && index < length - 1) {
      e.preventDefault();
      inputRefs.current[index + 1]?.focus();
    } else if (e.key === 'Escape' && onCancel) {
      e.preventDefault();
      onCancel();
    }
  };

  const handlePaste = (e: ClipboardEvent<HTMLInputElement>) => {
    e.preventDefault();
    const pastedData = e.clipboardData.getData('text/plain').trim();
    
    // Only accept digits
    const digits = pastedData.replace(/\D/g, '').slice(0, length);
    
    if (digits.length > 0) {
      const newOtp = [...otp];
      for (let i = 0; i < digits.length; i++) {
        if (i < length) {
          newOtp[i] = digits[i];
        }
      }
      setOtp(newOtp);
      
      // Focus the next empty input or the last input
      const nextEmptyIndex = newOtp.findIndex(d => d === '');
      const focusIndex = nextEmptyIndex === -1 ? length - 1 : Math.min(nextEmptyIndex, length - 1);
      inputRefs.current[focusIndex]?.focus();
    }
  };

  const handleFocus = (index: number) => {
    // Select the content on focus for easy overwriting
    inputRefs.current[index]?.select();
  };

  return (
    <div className="flex flex-col items-center space-y-4">
      <div className="flex space-x-2">
        {Array.from({ length }, (_, index) => (
          <input
            key={index}
            ref={(el) => {
              inputRefs.current[index] = el;
            }}
            type="text"
            inputMode="numeric"
            maxLength={1}
            value={otp[index]}
            onChange={(e) => handleChange(index, e.target.value)}
            onKeyDown={(e) => handleKeyDown(index, e)}
            onPaste={handlePaste}
            onFocus={() => handleFocus(index)}
            disabled={disabled}
            className={cn(
              'w-12 h-14 text-center text-2xl font-semibold',
              'border-2 rounded-lg',
              'focus:outline-none focus:ring-2 focus:ring-offset-2',
              'transition-all duration-200',
              error
                ? 'border-red-500 focus:ring-red-500'
                : 'border-gray-300 focus:border-blue-500 focus:ring-blue-500',
              disabled && 'opacity-50 cursor-not-allowed bg-gray-50',
              otp[index] && 'border-blue-500 bg-blue-50'
            )}
            aria-label={`Digit ${index + 1}`}
          />
        ))}
      </div>
      
      {error && (
        <p className="text-sm text-red-600 text-center" role="alert">
          {error}
        </p>
      )}
      
      <p className="text-sm text-gray-500 text-center">
        Enter the {length}-digit code sent to your registered mobile number
      </p>
    </div>
  );
}

