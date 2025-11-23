/**
 * Prisma seed script
 * Run with: pnpm db:seed or npx prisma db seed
 */
import bcrypt from 'bcryptjs';
import { PrismaClient } from '@prisma/client';

const prisma = new PrismaClient();

async function main() {
  console.log('Seeding database...');

  const defaultPassword = 'password123';
  const passwordHash = await bcrypt.hash(defaultPassword, 10);

  // Create mock users
  const users = [
    {
      email: 'john.doe@example.com',
      passwordHash,
      roles: ['customer'],
      permissions: ['read', 'transact', 'configure'],
      name: 'John Doe',
      beneficiaries: {
        create: [
          {
            nickname: 'Mom',
            fullName: 'Martha Doe',
            paymentAddress: 'martha.doe@upi',
            paymentType: 'upi',
            bankName: 'First National Bank',
          },
          {
            nickname: 'Landlord',
            fullName: 'Bob Smith',
            paymentAddress: 'ACC-987654321',
            paymentType: 'account',
            bankName: 'City Bank',
          },
        ],
      },
    },
    {
      email: 'jane.smith@example.com',
      passwordHash,
      roles: ['customer'],
      permissions: ['read', 'transact'],
      name: 'Jane Smith',
      beneficiaries: {
        create: [
          {
            nickname: 'Sister',
            fullName: 'Sarah Smith',
            paymentAddress: 'sarah.smith@upi',
            paymentType: 'upi',
            bankName: 'Credit Union',
          },
        ],
      },
    },
  ];

  for (const userData of users) {
    // Clean up existing data before re-seeding
    const existingUser = await prisma.user.findUnique({
      where: { email: userData.email },
      include: {
        beneficiaries: true,
        accounts: true,
        loans: true,
        transactions: true,
        paymentReminders: true,
        notificationPreferences: true,
      },
    });

    if (existingUser) {
      await prisma.beneficiary.deleteMany({
        where: { userId: existingUser.id },
      });
      await prisma.transaction.deleteMany({
        where: { userId: existingUser.id },
      });
      await prisma.loan.deleteMany({
        where: { userId: existingUser.id },
      });
      await prisma.account.deleteMany({
        where: { userId: existingUser.id },
      });
      await prisma.paymentReminder.deleteMany({
        where: { userId: existingUser.id },
      });
      await prisma.notificationPreference.deleteMany({
        where: { userId: existingUser.id },
      });
    }

    const user = await prisma.user.upsert({
      where: { email: userData.email },
      update: {
        beneficiaries: userData.beneficiaries,
      },
      create: userData,
    });
    console.log(`✓ User created/updated: ${user.email}`);

    // Create accounts for user
    const accounts = await Promise.all([
      prisma.account.create({
        data: {
          userId: user.id,
          accountNumber: `CHK-${user.id.slice(0, 8)}-001`,
          accountType: 'checking',
          balance: 5000.0,
          currency: 'USD',
          status: 'active',
        },
      }),
      prisma.account.create({
        data: {
          userId: user.id,
          accountNumber: `SAV-${user.id.slice(0, 8)}-002`,
          accountType: 'savings',
          balance: 15000.0,
          currency: 'USD',
          status: 'active',
        },
      }),
      prisma.account.create({
        data: {
          userId: user.id,
          accountNumber: `CC-${user.id.slice(0, 8)}-003`,
          accountType: 'credit_card',
          balance: 500.0, // Current balance (debt)
          creditLimit: 10000.0,
          currency: 'USD',
          status: 'active',
        },
      }),
    ]);
    console.log(`✓ Created ${accounts.length} accounts for ${user.email}`);

    // Create loans for user
    const loans = await Promise.all([
      prisma.loan.create({
        data: {
          userId: user.id,
          loanType: 'mortgage',
          loanNumber: `MORT-${user.id.slice(0, 8)}-001`,
          outstandingBalance: 250000.0,
          interestRate: 0.0375, // 3.75%
          monthlyPayment: 1200.0,
          remainingTermMonths: 240,
          nextPaymentDate: new Date(Date.now() + 15 * 24 * 60 * 60 * 1000), // 15 days from now
        },
      }),
      prisma.loan.create({
        data: {
          userId: user.id,
          loanType: 'auto',
          loanNumber: `AUTO-${user.id.slice(0, 8)}-001`,
          outstandingBalance: 15000.0,
          interestRate: 0.045, // 4.5%
          monthlyPayment: 350.0,
          remainingTermMonths: 48,
          nextPaymentDate: new Date(Date.now() + 20 * 24 * 60 * 60 * 1000), // 20 days from now
        },
      }),
    ]);
    console.log(`✓ Created ${loans.length} loans for ${user.email}`);

    // Get beneficiaries for transaction linking
    const beneficiaries = await prisma.beneficiary.findMany({
      where: { userId: user.id },
    });

    // Create sample transactions
    const transactions = await Promise.all([
      // Completed transactions
      prisma.transaction.create({
        data: {
          userId: user.id,
          accountId: accounts[0].id, // Checking account
          transactionType: 'payment',
          amount: 100.0,
          currency: 'USD',
          fromAccount: accounts[0].accountNumber,
          toAccount: beneficiaries[0]?.paymentAddress || 'external@upi',
          beneficiaryId: beneficiaries[0]?.id,
          description: 'Payment to Mom',
          status: 'completed',
          referenceNumber: `TXN-${new Date().toISOString().slice(0, 10).replace(/-/g, '')}-${Math.random().toString(36).substring(2, 8).toUpperCase()}`,
          completedAt: new Date(Date.now() - 2 * 24 * 60 * 60 * 1000), // 2 days ago
        },
      }),
      prisma.transaction.create({
        data: {
          userId: user.id,
          accountId: accounts[0].id,
          transactionType: 'transfer',
          amount: 500.0,
          currency: 'USD',
          fromAccount: accounts[0].accountNumber,
          toAccount: accounts[1].accountNumber, // Internal transfer to savings
          description: 'Transfer to savings',
          status: 'completed',
          referenceNumber: `TXN-${new Date().toISOString().slice(0, 10).replace(/-/g, '')}-${Math.random().toString(36).substring(2, 8).toUpperCase()}`,
          completedAt: new Date(Date.now() - 1 * 24 * 60 * 60 * 1000), // 1 day ago
        },
      }),
      // Pending transaction
      prisma.transaction.create({
        data: {
          userId: user.id,
          accountId: accounts[0].id,
          transactionType: 'payment',
          amount: 200.0,
          currency: 'USD',
          fromAccount: accounts[0].accountNumber,
          toAccount: beneficiaries[1]?.paymentAddress || 'external@account',
          beneficiaryId: beneficiaries[1]?.id,
          description: 'Payment to Landlord',
          status: 'pending',
          expiresAt: new Date(Date.now() + 10 * 60 * 1000), // 10 minutes from now
        },
      }),
    ]);
    console.log(`✓ Created ${transactions.length} transactions for ${user.email}`);

    // Create payment reminders
    const reminders = await Promise.all([
      prisma.paymentReminder.create({
        data: {
          userId: user.id,
          scheduledDate: new Date(Date.now() + 7 * 24 * 60 * 60 * 1000), // 7 days from now
          amount: 500.0,
          recipient: 'Mom',
          description: 'Monthly allowance',
          beneficiaryId: beneficiaries[0]?.id,
          accountId: accounts[0].id,
          isCompleted: false,
          reminderNotificationSettings: {
            email: true,
            sms: false,
            push: true,
          },
        },
      }),
      prisma.paymentReminder.create({
        data: {
          userId: user.id,
          scheduledDate: new Date(Date.now() + 14 * 24 * 60 * 60 * 1000), // 14 days from now
          amount: 1200.0,
          recipient: 'Landlord',
          description: 'Monthly rent payment',
          beneficiaryId: beneficiaries[1]?.id,
          accountId: accounts[0].id,
          isCompleted: false,
          reminderNotificationSettings: {
            email: true,
            sms: true,
            push: false,
          },
        },
      }),
      prisma.paymentReminder.create({
        data: {
          userId: user.id,
          scheduledDate: new Date(Date.now() - 5 * 24 * 60 * 60 * 1000), // 5 days ago (completed)
          amount: 300.0,
          recipient: 'Electric Company',
          description: 'Utility bill payment',
          accountId: accounts[1].id,
          isCompleted: true,
          reminderNotificationSettings: {
            email: true,
            sms: false,
            push: false,
          },
        },
      }),
    ]);
    console.log(`✓ Created ${reminders.length} payment reminders for ${user.email}`);

    // Create notification preferences
    const preferences = await Promise.all([
      prisma.notificationPreference.create({
        data: {
          userId: user.id,
          channel: 'email',
          eventType: 'payment',
          isEnabled: true,
        },
      }),
      prisma.notificationPreference.create({
        data: {
          userId: user.id,
          channel: 'sms',
          eventType: 'alert',
          isEnabled: true,
        },
      }),
      prisma.notificationPreference.create({
        data: {
          userId: user.id,
          channel: 'push',
          eventType: 'balance',
          isEnabled: true,
        },
      }),
    ]);
    console.log(`✓ Created ${preferences.length} notification preferences for ${user.email}`);
  }

  console.log('Seeding completed!');
}

main()
  .catch((e) => {
    console.error('Error seeding database:', e);
    process.exit(1);
  })
  .finally(async () => {
    await prisma.$disconnect();
  });
