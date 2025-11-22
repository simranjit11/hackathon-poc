import { NextRequest } from 'next/server';
import { validateAccessToken, extractTokenFromHeader } from '@/lib/auth';
import { corsResponse, corsPreflight } from '@/lib/cors';
import {
    updateReminder,
    deleteReminder,
    type UpdateReminderInput,
} from '@/lib/banking/reminders';

/**
 * PUT /api/banking/reminders/[id]
 * Update an existing payment reminder
 */
export async function PUT(
    request: NextRequest,
    { params }: { params: Promise<{ id: string }> }
) {
    if (request.method === 'OPTIONS') {
        return corsPreflight();
    }

    try {
        const authHeader = request.headers.get('Authorization');
        const token = extractTokenFromHeader(authHeader);
        const user = await validateAccessToken(token);

        const reminderId = params.id;
        const body = await request.json();

        const input: UpdateReminderInput = {};

        if (body.scheduledDate !== undefined) {
            const scheduledDate = new Date(body.scheduledDate);
            if (isNaN(scheduledDate.getTime())) {
                return corsResponse(
                    { error: 'Invalid scheduledDate format. Use ISO 8601 format' },
                    400
                );
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

        const reminder = await updateReminder(user.user_id, reminderId, input);

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

        if (error instanceof Error && error.message.includes('missing')) {
            return corsResponse({ error: 'Authorization header is required' }, 401);
        }

        if (
            error instanceof Error &&
            (error.message.includes('Invalid') || error.message.includes('expired'))
        ) {
            return corsResponse({ error: error.message }, 401);
        }

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
                return corsResponse({ error: error.message }, 409);
            }
        }

        return corsResponse({ error: 'Internal server error' }, 500);
    }
}

/**
 * DELETE /api/banking/reminders/[id]
 * Delete a payment reminder
 */
export async function DELETE(
    request: NextRequest,
    { params }: { params: Promise<{ id: string }> }
) {
    if (request.method === 'OPTIONS') {
        return corsPreflight();
    }

    try {
        const authHeader = request.headers.get('Authorization');
        const token = extractTokenFromHeader(authHeader);
        const user = await validateAccessToken(token);

        const { id: reminderId } = await params;

        await deleteReminder(user.user_id, reminderId);

        return corsResponse(null, 204);
    } catch (error) {
        console.error('Error deleting reminder:', error);

        if (error instanceof Error && error.message.includes('missing')) {
            return corsResponse({ error: 'Authorization header is required' }, 401);
        }

        if (
            error instanceof Error &&
            (error.message.includes('Invalid') || error.message.includes('expired'))
        ) {
            return corsResponse({ error: error.message }, 401);
        }

        if (error instanceof Error) {
            // Not found errors
            if (error.message.includes('not found') || error.message.includes('does not belong')) {
                return corsResponse({ error: error.message }, 404);
            }
        }

        return corsResponse({ error: 'Internal server error' }, 500);
    }
}

