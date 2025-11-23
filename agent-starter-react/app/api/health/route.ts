import { NextResponse } from 'next/server';
import { prisma } from '@/lib/db/prisma';
import { testRedisConnection } from '@/lib/db/redis';

/**
 * GET /api/health
 * Health check endpoint for database connections
 */
export async function GET() {
  const health: {
    status: 'healthy' | 'unhealthy';
    postgres: 'connected' | 'disconnected';
    redis: 'connected' | 'disconnected';
    timestamp: string;
  } = {
    status: 'healthy',
    postgres: 'disconnected',
    redis: 'disconnected',
    timestamp: new Date().toISOString(),
  };

  // Test PostgreSQL connection
  try {
    await prisma.$queryRaw`SELECT 1`;
    health.postgres = 'connected';
  } catch (error) {
    console.error('PostgreSQL health check failed:', error);
    health.postgres = 'disconnected';
    health.status = 'unhealthy';
  }

  // Test Redis connection
  try {
    const redisConnected = await testRedisConnection();
    health.redis = redisConnected ? 'connected' : 'disconnected';
    if (!redisConnected) {
      health.status = 'unhealthy';
    }
  } catch (error) {
    console.error('Redis health check failed:', error);
    health.redis = 'disconnected';
    health.status = 'unhealthy';
  }

  return NextResponse.json(health, {
    status: health.status === 'healthy' ? 200 : 503,
  });
}
