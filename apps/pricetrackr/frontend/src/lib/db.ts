import postgres from 'postgres';

function normalizePostgresConnectionString(value: string): string {
  const trimmed = value.trim();
  if (trimmed.startsWith("postgresql+asyncpg://")) {
    return `postgresql://${trimmed.slice("postgresql+asyncpg://".length)}`;
  }
  if (trimmed.startsWith("postgres://")) {
    return `postgresql://${trimmed.slice("postgres://".length)}`;
  }
  return trimmed;
}

const connectionString = normalizePostgresConnectionString(
  process.env.DATABASE_POOLED_URL || process.env.DATABASE_URL || ''
);
const caCertificate = process.env.AIVEN_CA_CERT?.replace(/\\n/g, "\n").trim();

if (!connectionString) {
  console.warn("Warning: Neither DATABASE_POOLED_URL nor DATABASE_URL is configured in environment variables.");
}

if (connectionString && !caCertificate) {
  throw new Error("AIVEN_CA_CERT is required when the PriceTrackr database is configured.");
}

export const sql: any = connectionString
  ? postgres(connectionString, {
      ssl: {
        ca: caCertificate,
        rejectUnauthorized: true,
      },
      max: 1,
      idle_timeout: 20,
      connect_timeout: 10,
      prepare: false,
    })
  : ((...args: any[]) => {
      console.warn("Warning: Database query attempted but connection string is missing.");
      return Promise.resolve([]);
    });
