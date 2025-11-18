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
    },
    {
      email: 'jane.smith@example.com',
      passwordHash,
      roles: ['customer'],
      permissions: ['read', 'transact'],
      name: 'Jane Smith',
    },
  ];

  for (const userData of users) {
    const user = await prisma.user.upsert({
      where: { email: userData.email },
      update: {},
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

