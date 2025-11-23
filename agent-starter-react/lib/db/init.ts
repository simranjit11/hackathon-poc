/**
 * Database initialization using Prisma
 * Run migrations and seed data on startup
 */
import { createUser, getDefaultPassword } from '../users';
import { prisma } from './prisma';
import { testRedisConnection } from './redis';

/**
 * Initialize all database connections and run migrations
 * Call this on application startup
 */
export async function initializeDatabases(): Promise<void> {
  console.log('Initializing databases...');

  // Prisma migrations are handled via `prisma migrate deploy` or `prisma migrate dev`
  // For production, run migrations separately before starting the app
  // For development, migrations run automatically via `prisma migrate dev`

  try {
    // Test database connection
    await prisma.$connect();
    console.log('✓ PostgreSQL connected via Prisma');

    // Seed mock users if they don't exist
    await seedMockUsers();
  } catch (error) {
    console.error('✗ PostgreSQL initialization failed:', error);
    throw error;
  }

  // Test Redis connection
  try {
    const redisConnected = await testRedisConnection();
    if (redisConnected) {
      console.log('✓ Redis connected');
    } else {
      console.warn('⚠ Redis connection failed - OTP and session features may not work');
    }
  } catch (error) {
    console.warn('⚠ Redis connection test failed:', error);
    // Don't throw - Redis is optional for some features
  }

  console.log('Database initialization complete');
}

/**
 * Seed mock users for testing
 */
async function seedMockUsers(): Promise<void> {
  const mockUsers = [
    {
      email: 'john.doe@example.com',
      password: getDefaultPassword(),
      roles: ['customer'],
      permissions: ['read', 'transact', 'configure'],
      name: 'John Doe',
    },
    {
      email: 'jane.smith@example.com',
      password: getDefaultPassword(),
      roles: ['customer'],
      permissions: ['read', 'transact'],
      name: 'Jane Smith',
    },
  ];

  for (const userData of mockUsers) {
    try {
      const existing = await prisma.user.findUnique({
        where: { email: userData.email },
      });

      if (!existing) {
        await createUser(
          userData.email,
          userData.password,
          userData.roles,
          userData.permissions,
          userData.name
        );
        console.log(`✓ Seeded user: ${userData.email}`);
      }
    } catch (error) {
      console.error(`Error seeding user ${userData.email}:`, error);
    }
  }
}

/**
 * Test database connections
 */
export async function testConnections(): Promise<{ postgres: boolean; redis: boolean }> {
  const results = {
    postgres: false,
    redis: false,
  };

  try {
    await prisma.$queryRaw`SELECT 1`;
    results.postgres = true;
  } catch (error) {
    console.error('PostgreSQL test failed:', error);
  }

  try {
    results.redis = await testRedisConnection();
  } catch (error) {
    console.error('Redis test failed:', error);
  }

  return results;
}
