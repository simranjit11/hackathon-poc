import { NextRequest } from 'next/server';
import { requireApiKey } from '@/lib/api-key-auth';
import { type UpdateReminderInput, deleteReminder, updateReminder } from '@/lib/banking/reminders';
import { corsPreflight, corsResponse } from '@/lib/cors';

/**
 * PUT /api/internal/banking/reminders/[id]
 * Update an existing payment reminder (server-to-server)
 * Requires API key authentication
 */
export async function PUT(request: NextRequest, { params }: { params: Promise<{ id: string }> }) {
  if (request.method === 'OPTIONS') {
    return corsPreflight();
  }

  // Require API key authentication
  const authError = requireApiKey(request);
  if (authError) {
    return authError;
  }

  try {
    const { id: reminderId } = await params;
    const body = await request.json();

    // Validate required fields
    if (!body.userId) {
      return corsResponse({ error: 'userId is required' }, 400);
    }

    const input: UpdateReminderInput = {};

    if (body.scheduledDate !== undefined) {
      const scheduledDate = new Date(body.scheduledDate);
      if (isNaN(scheduledDate.getTime())) {
        return corsResponse({ error: 'Invalid scheduledDate format. Use ISO 8601 format' }, 400);
      }
      input.scheduledDate = scheduledDate;
    }

    if (body.amount !== undefined) {
      input.amount = Number(body.amount);
    }

    if (body.recipient !== undefined) {
      input.recipient = body.recipient;
    }

    if (body.description !== undefined) {
      input.description = body.description;
    }

    if (body.reminderNotificationSettings !== undefined) {
      input.reminderNotificationSettings = body.reminderNotificationSettings;
    }

    if (body.isCompleted !== undefined) {
      input.isCompleted = Boolean(body.isCompleted);
    }

    const reminder = await updateReminder(body.userId, reminderId, input);

    return corsResponse(
      {
        data: {
          id: reminder.id,
          scheduledDate: reminder.scheduledDate.toISOString(),
          amount: Number(reminder.amount),
          recipient: reminder.recipient,
          description: reminder.description,
          beneficiaryId: reminder.beneficiaryId,
          accountId: reminder.accountId,
          isCompleted: reminder.isCompleted,
          reminderNotificationSettings: reminder.reminderNotificationSettings,
          createdAt: reminder.createdAt.toISOString(),
          updatedAt: reminder.updatedAt.toISOString(),
          beneficiary: reminder.beneficiary
            ? {
                id: reminder.beneficiary.id,
                nickname: reminder.beneficiary.nickname,
                fullName: reminder.beneficiary.fullName,
                paymentAddress: reminder.beneficiary.paymentAddress,
              }
            : null,
          account: {
            id: reminder.account.id,
            accountNumber: reminder.account.accountNumber,
            accountType: reminder.account.accountType,
          },
        },
      },
      200
    );
  } catch (error) {
    console.error('Error updating reminder:', error);

    if (error instanceof Error) {
      // Not found errors
      if (error.message.includes('not found') || error.message.includes('does not belong')) {
        return corsResponse({ error: error.message }, 404);
      }

      // Validation errors
      if (
        error.message.includes('must be in the future') ||
        error.message.includes('must be positive') ||
        error.message.includes('Cannot modify')
      ) {
        return corsResponse({ error: error.message }, 400);
      }
    }

    return corsResponse(
      { error: error instanceof Error ? error.message : 'Internal server error' },
      500
    );
  }
}

/**
 * DELETE /api/internal/banking/reminders/[id]
 * Delete a payment reminder (server-to-server)
 * Requires API key authentication
 */
export async function DELETE(
  request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  if (request.method === 'OPTIONS') {
    return corsPreflight();
  }

  // Require API key authentication
  const authError = requireApiKey(request);
  if (authError) {
    return authError;
  }

  try {
    const { id: reminderId } = await params;
    const searchParams = request.nextUrl.searchParams;
    const userId = searchParams.get('userId');

    if (!userId) {
      return corsResponse({ error: 'userId is required as query parameter' }, 400);
    }

    await deleteReminder(userId, reminderId);

    return corsResponse(null, 204);
  } catch (error) {
    console.error('Error deleting reminder:', error);

    if (error instanceof Error) {
      // Not found errors
      if (error.message.includes('not found') || error.message.includes('does not belong')) {
        return corsResponse({ error: error.message }, 404);
      }
    }

    return corsResponse(
      { error: error instanceof Error ? error.message : 'Internal server error' },
      500
    );
  }
}

export async function OPTIONS() {
  return corsPreflight();
}
