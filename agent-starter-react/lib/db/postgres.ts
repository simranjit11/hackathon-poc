import { Pool, PoolClient } from 'pg';

/**
 * PostgreSQL connection pool
 * Singleton pattern to reuse connections
 */

let pool: Pool | null = null;

/**
 * Get or create PostgreSQL connection pool
 *
 * @returns PostgreSQL connection pool
 */
export function getPostgresPool(): Pool {
  if (pool) {
    return pool;
  }

  const connectionString =
    process.env.DATABASE_URL ||
    `postgresql://${process.env.DB_USER || 'postgres'}:${process.env.DB_PASSWORD || 'postgres'}@${process.env.DB_HOST || 'localhost'}:${process.env.DB_PORT || '5432'}/${process.env.DB_NAME || 'voice_assistant'}`;

  pool = new Pool({
    connectionString,
    max: 20, // Maximum number of clients in the pool
    idleTimeoutMillis: 30000,
    connectionTimeoutMillis: 2000,
  });

  // Handle pool errors
  pool.on('error', (err) => {
    console.error('Unexpected error on idle PostgreSQL client', err);
  });

  return pool;
}

/**
 * Execute a query with automatic connection management
 *
 * @param query - SQL query string
 * @param params - Query parameters
 * @returns Query result
 */
export async function query<T = any>(queryText: string, params?: any[]): Promise<T[]> {
  const pool = getPostgresPool();
  const result = await pool.query(queryText, params);
  return result.rows as T[];
}

/**
 * Execute a query and return a single row
 *
 * @param query - SQL query string
 * @param params - Query parameters
 * @returns Single row or null
 */
export async function queryOne<T = any>(queryText: string, params?: any[]): Promise<T | null> {
  const rows = await query<T>(queryText, params);
  return rows.length > 0 ? rows[0] : null;
}

/**
 * Execute a transaction
 *
 * @param callback - Transaction callback function
 * @returns Transaction result
 */
export async function transaction<T>(callback: (client: PoolClient) => Promise<T>): Promise<T> {
  const pool = getPostgresPool();
  const client = await pool.connect();

  try {
    await client.query('BEGIN');
    const result = await callback(client);
    await client.query('COMMIT');
    return result;
  } catch (error) {
    await client.query('ROLLBACK');
    throw error;
  } finally {
    client.release();
  }
}

/**
 * Close the connection pool (for cleanup)
 */
export async function closePool(): Promise<void> {
  if (pool) {
    await pool.end();
    pool = null;
  }
}
