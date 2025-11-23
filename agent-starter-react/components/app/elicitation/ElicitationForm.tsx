/**
 * Dynamic Elicitation Form Component
 * ===================================
 * Renders form fields based on elicitation schema with validation.
 */

'use client';

import { FormEvent, useState } from 'react';
import type { ElicitationField } from '@/lib/elicitation-types';
import { validateField } from '@/lib/elicitation-types';
import { cn } from '@/lib/utils';

/**
 * Dynamic Elicitation Form Component
 * ===================================
 * Renders form fields based on elicitation schema with validation.
 */

/**
 * Dynamic Elicitation Form Component
 * ===================================
 * Renders form fields based on elicitation schema with validation.
 */

/**
 * Dynamic Elicitation Form Component
 * ===================================
 * Renders form fields based on elicitation schema with validation.
 */

export interface ElicitationFormProps {
  fields: ElicitationField[];
  onSubmit: (values: Record<string, any>) => void;
  onCancel: () => void;
  disabled?: boolean;
  error?: string;
}

export function ElicitationForm({
  fields,
  onSubmit,
  onCancel,
  disabled = false,
  error,
}: ElicitationFormProps) {
  const [values, setValues] = useState<Record<string, any>>(() =>
    fields.reduce(
      (acc, field) => {
        acc[field.name] = field.field_type === 'boolean' ? false : '';
        return acc;
      },
      {} as Record<string, any>
    )
  );

  const [errors, setErrors] = useState<Record<string, string>>({});
  const [touched, setTouched] = useState<Record<string, boolean>>({});

  const handleChange = (name: string, value: any) => {
    setValues((prev) => ({ ...prev, [name]: value }));

    // Clear error when user starts typing
    if (errors[name]) {
      setErrors((prev) => {
        const newErrors = { ...prev };
        delete newErrors[name];
        return newErrors;
      });
    }
  };

  const handleBlur = (name: string) => {
    setTouched((prev) => ({ ...prev, [name]: true }));

    // Validate field on blur
    const field = fields.find((f) => f.name === name);
    if (field) {
      const error = validateField(values[name], field.validation);
      if (error) {
        setErrors((prev) => ({ ...prev, [name]: error }));
      }
    }
  };

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();

    // Validate all fields
    const newErrors: Record<string, string> = {};
    fields.forEach((field) => {
      const error = validateField(values[field.name], field.validation);
      if (error) {
        newErrors[field.name] = error;
      }
    });

    if (Object.keys(newErrors).length > 0) {
      setErrors(newErrors);
      setTouched(
        fields.reduce(
          (acc, field) => {
            acc[field.name] = true;
            return acc;
          },
          {} as Record<string, boolean>
        )
      );
      return;
    }

    onSubmit(values);
  };

  const renderField = (field: ElicitationField) => {
    const hasError = touched[field.name] && errors[field.name];

    switch (field.field_type) {
      case 'text':
      case 'otp':
        return (
          <input
            type="text"
            id={field.name}
            value={values[field.name]}
            onChange={(e) => handleChange(field.name, e.target.value)}
            onBlur={() => handleBlur(field.name)}
            placeholder={field.placeholder}
            disabled={disabled}
            className={cn(
              'w-full rounded-lg border px-3 py-2',
              'focus:ring-2 focus:ring-offset-2 focus:outline-none',
              'transition-colors duration-200',
              hasError
                ? 'border-red-500 focus:ring-red-500'
                : 'border-gray-300 focus:ring-blue-500',
              disabled && 'cursor-not-allowed bg-gray-50 opacity-50'
            )}
          />
        );

      case 'number':
        return (
          <input
            type="number"
            id={field.name}
            value={values[field.name]}
            onChange={(e) => handleChange(field.name, parseFloat(e.target.value) || '')}
            onBlur={() => handleBlur(field.name)}
            placeholder={field.placeholder}
            disabled={disabled}
            min={field.validation?.min_value}
            max={field.validation?.max_value}
            className={cn(
              'w-full rounded-lg border px-3 py-2',
              'focus:ring-2 focus:ring-offset-2 focus:outline-none',
              'transition-colors duration-200',
              hasError
                ? 'border-red-500 focus:ring-red-500'
                : 'border-gray-300 focus:ring-blue-500',
              disabled && 'cursor-not-allowed bg-gray-50 opacity-50'
            )}
          />
        );

      case 'boolean':
        return (
          <div className="flex items-center">
            <input
              type="checkbox"
              id={field.name}
              checked={values[field.name]}
              onChange={(e) => handleChange(field.name, e.target.checked)}
              disabled={disabled}
              className={cn(
                'h-4 w-4 rounded border-gray-300 text-blue-600',
                'focus:ring-2 focus:ring-blue-500',
                disabled && 'cursor-not-allowed opacity-50'
              )}
            />
            <label htmlFor={field.name} className="ml-2 text-sm text-gray-700">
              {field.label}
            </label>
          </div>
        );

      case 'select':
        return (
          <select
            id={field.name}
            value={values[field.name]}
            onChange={(e) => handleChange(field.name, e.target.value)}
            onBlur={() => handleBlur(field.name)}
            disabled={disabled}
            className={cn(
              'w-full rounded-lg border px-3 py-2',
              'focus:ring-2 focus:ring-offset-2 focus:outline-none',
              'transition-colors duration-200',
              hasError
                ? 'border-red-500 focus:ring-red-500'
                : 'border-gray-300 focus:ring-blue-500',
              disabled && 'cursor-not-allowed bg-gray-50 opacity-50'
            )}
          >
            <option value="">Select...</option>
            {field.options?.map((option) => (
              <option key={option} value={option}>
                {option}
              </option>
            ))}
          </select>
        );

      default:
        return null;
    }
  };

  return (
    <form onSubmit={handleSubmit} className="mx-auto max-w-md space-y-4">
      {fields.map((field) =>
        field.field_type !== 'boolean' ? (
          <div key={field.name}>
            <label htmlFor={field.name} className="mb-1 block text-sm font-medium text-gray-700">
              {field.label}
              {field.validation?.required && <span className="ml-1 text-red-500">*</span>}
            </label>
            {renderField(field)}
            {touched[field.name] && errors[field.name] && (
              <p className="mt-1 text-sm text-red-600">{errors[field.name]}</p>
            )}
            {field.help_text && !errors[field.name] && (
              <p className="mt-1 text-sm text-gray-500">{field.help_text}</p>
            )}
          </div>
        ) : (
          <div key={field.name}>
            {renderField(field)}
            {field.help_text && (
              <p className="mt-1 ml-6 text-sm text-gray-500">{field.help_text}</p>
            )}
          </div>
        )
      )}

      {error && (
        <div className="rounded-md bg-red-50 p-4">
          <p className="text-sm text-red-700">{error}</p>
        </div>
      )}

      <div className="flex space-x-3 pt-2">
        <button
          type="button"
          onClick={onCancel}
          disabled={disabled}
          className={cn(
            'flex-1 rounded-lg border border-gray-300 px-4 py-2',
            'bg-white text-sm font-medium text-gray-700',
            'hover:bg-gray-50 focus:ring-2 focus:outline-none',
            'focus:ring-gray-500 focus:ring-offset-2',
            'transition-colors duration-200',
            disabled && 'cursor-not-allowed opacity-50'
          )}
        >
          Cancel
        </button>

        <button
          type="submit"
          disabled={disabled}
          className={cn(
            'flex-1 rounded-lg border border-transparent px-4 py-2',
            'bg-blue-600 text-sm font-medium text-white',
            'hover:bg-blue-700 focus:ring-2 focus:outline-none',
            'focus:ring-blue-500 focus:ring-offset-2',
            'transition-colors duration-200',
            disabled && 'cursor-not-allowed opacity-50'
          )}
        >
          Submit
        </button>
      </div>
    </form>
  );
}
