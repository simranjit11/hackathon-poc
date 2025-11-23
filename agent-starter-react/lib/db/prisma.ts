import { PrismaClient } from '@prisma/client';

/**
 * Prisma Client singleton
 * Prevents multiple instances in development
 * 
 * Prisma uses connection pooling by default - connections are opened on-demand
 * and reused from a pool. No need to manually manage connections.
 */

declare global {
  // eslint-disable-next-line no-var
  var prisma: PrismaClient | undefined;
}

export const prisma =
  globalThis.prisma ??
  new PrismaClient({
    log: process.env.NODE_ENV === 'development' ? ['query', 'error', 'warn'] : ['error'],
    // Connection pool settings (optional - Prisma has sensible defaults)
    // These are set via DATABASE_URL connection string parameters:
    // - connection_limit: max connections in pool (default: based on database)
    // - pool_timeout: timeout for getting connection from pool (default: 10s)
    // Prisma opens connections on-demand and reuses them efficiently
  });

if (process.env.NODE_ENV !== 'production') {
  globalThis.prisma = prisma;
}

/**
 * Disconnect Prisma client (for cleanup)
 */
export async function disconnectPrisma(): Promise<void> {
  await prisma.$disconnect();
}
