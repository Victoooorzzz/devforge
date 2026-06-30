import { neon } from '@neondatabase/serverless';

function normalizeNeonConnectionString(value: string): string {
  const trimmed = value.trim();
  if (trimmed.startsWith("postgresql+asyncpg://")) {
    return `postgresql://${trimmed.slice("postgresql+asyncpg://".length)}`;
  }
  if (trimmed.startsWith("postgres://")) {
    return `postgresql://${trimmed.slice("postgres://".length)}`;
  }
  return trimmed;
}

const connectionString = normalizeNeonConnectionString(process.env.DATABASE_POOLED_URL || process.env.DATABASE_URL || '');

if (!connectionString) {
  console.warn("Warning: Neither DATABASE_POOLED_URL nor DATABASE_URL is configured in environment variables.");
}

export const sql = connectionString
  ? neon(connectionString)
  : ((...args: any[]) => {
      console.warn("Warning: Database query attempted but connection string is missing.");
      return Promise.resolve([]);
    }) as any;
