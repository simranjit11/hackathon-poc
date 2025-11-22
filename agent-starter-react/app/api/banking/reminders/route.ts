import { NextRequest } from 'next/server';
import { validateAccessToken, extractTokenFromHeader } from '@/lib/auth';
import { corsResponse, corsPreflight } from '@/lib/cors';
import {
    getReminders,
    createReminder,
    type CreateReminderInput,
} from '@/lib/banking/reminders';

/**
 * GET /api/banking/reminders
 * Retrieve all payment reminders for authenticated user
 */
export async function GET(request: NextRequest) {
    if (request.method === 'OPTIONS') {
        return corsPreflight();
    }

    try {
        const authHeader = request.headers.get('Authorization');
        const token = extractTokenFromHeader(authHeader);
        const user = await validateAccessToken(token);

        // Parse query parameters
        const searchParams = request.nextUrl.searchParams;
        const isCompletedParam = searchParams.get('isCompleted');
        const scheduledDateFromParam = searchParams.get('scheduledDateFrom');
        const scheduledDateToParam = searchParams.get('scheduledDateTo');

        const filters: {
            isCompleted?: boolean;
            scheduledDateFrom?: Date;
            scheduledDateTo?: Date;
        } = {};

        if (isCompletedParam !== null) {
            filters.isCompleted = isCompletedParam === 'true';
        }

        if (scheduledDateFromParam) {
            filters.scheduledDateFrom = new Date(scheduledDateFromParam);
        }

        if (scheduledDateToParam) {
            filters.scheduledDateTo = new Date(scheduledDateToParam);
        }

        const reminders = await getReminders(user.user_id, filters);

        return corsResponse(
            {
                data: reminders.map((reminder) => ({
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
                })),
            },
            200
        );
    } catch (error) {
        console.error('Error fetching reminders:', error);

        if (error instanceof Error && error.message.includes('missing')) {
            return corsResponse({ error: 'Authorization header is required' }, 401);
        }

        if (
            error instanceof Error &&
            (error.message.includes('Invalid') || error.message.includes('expired'))
        ) {
            return corsResponse({ error: error.message }, 401);
        }

        return corsResponse({ error: 'Internal server error' }, 500);
    }
}

/**
 * POST /api/banking/reminders
 * Create a new payment reminder
 */
export async function POST(request: NextRequest) {
    if (request.method === 'OPTIONS') {
        return corsPreflight();
    }

    try {
        const authHeader = request.headers.get('Authorization');
        const token = extractTokenFromHeader(authHeader);
        const user = await validateAccessToken(token);

        const body = await request.json();

        // Validate required fields
        if (!body.scheduledDate) {
            return corsResponse(
                { error: 'scheduledDate is required' },
                400
            );
        }

        if (!body.amount) {
            return corsResponse({ error: 'amount is required' }, 400);
        }

        if (!body.recipient) {
            return corsResponse({ error: 'recipient is required' }, 400);
        }

        if (!body.accountId) {
            return corsResponse({ error: 'accountId is required' }, 400);
        }

        // Parse scheduled date
        const scheduledDate = new Date(body.scheduledDate);
        if (isNaN(scheduledDate.getTime())) {
            return corsResponse(
                { error: 'Invalid scheduledDate format. Use ISO 8601 format' },
                400
            );
        }

        const input: CreateReminderInput = {
            scheduledDate,
            amount: Number(body.amount),
            recipient: body.recipient,
            description: body.description,
            beneficiaryId: body.beneficiaryId,
            beneficiaryNickname: body.beneficiaryNickname,
            accountId: body.accountId,
            reminderNotificationSettings: body.reminderNotificationSettings,
        };

        const reminder = await createReminder(user.user_id, input);

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
            201
        );
    } catch (error) {
        console.error('Error creating reminder:', error);

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
            // Validation errors
            if (
                error.message.includes('must be in the future') ||
                error.message.includes('must be positive') ||
                error.message.includes('not found') ||
                error.message.includes('does not belong')
            ) {
                return corsResponse({ error: error.message }, 400);
            }
        }

        return corsResponse({ error: 'Internal server error' }, 500);
    }
}

