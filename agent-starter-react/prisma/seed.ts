/**
 * Prisma seed script
 * Run with: pnpm db:seed or npx prisma db seed
 */

import { PrismaClient } from '@prisma/client';
import bcrypt from 'bcryptjs';

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
    // Clean up existing beneficiaries before re-seeding
    const existingUser = await prisma.user.findUnique({
        where: { email: userData.email },
        include: { beneficiaries: true }
    });
    
    if (existingUser) {
        await prisma.beneficiary.deleteMany({
            where: { userId: existingUser.id }
        });
    }

    const user = await prisma.user.upsert({
      where: { email: userData.email },
      update: {
        beneficiaries: userData.beneficiaries
      },
      create: userData,
    });
    console.log(`✓ User created/updated: ${user.email}`);
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
