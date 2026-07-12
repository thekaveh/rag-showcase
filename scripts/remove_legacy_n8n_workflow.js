"use strict";

// One-time migration for the workflow identity used before Atlas consumer
// workflow ownership. Deleting this exact row cascades its stale webhook row;
// n8n's unpublish CLI leaves that row behind and blocks the namespaced route.
const { Client } = require("pg");

const LEGACY_ID = "adaptiverag00001";
const schema = process.env.DB_POSTGRESDB_SCHEMA || "n8n";
if (!/^[A-Za-z_][A-Za-z0-9_]*$/.test(schema)) {
  throw new Error(`Unsafe DB_POSTGRESDB_SCHEMA: ${schema}`);
}

for (const name of [
  "DB_POSTGRESDB_HOST",
  "DB_POSTGRESDB_DATABASE",
  "DB_POSTGRESDB_USER",
  "DB_POSTGRESDB_PASSWORD",
]) {
  if (!process.env[name]) throw new Error(`${name} is required`);
}

const client = new Client({
  host: process.env.DB_POSTGRESDB_HOST,
  port: Number(process.env.DB_POSTGRESDB_PORT || 5432),
  database: process.env.DB_POSTGRESDB_DATABASE,
  user: process.env.DB_POSTGRESDB_USER,
  password: process.env.DB_POSTGRESDB_PASSWORD,
});

async function main() {
  await client.connect();
  try {
    const result = await client.query(
      `DELETE FROM "${schema}"."workflow_entity" WHERE id = $1 RETURNING id`,
      [LEGACY_ID],
    );
    if (result.rowCount !== 1) {
      throw new Error(`Expected one legacy workflow row, deleted ${result.rowCount}`);
    }
    console.log(`Removed legacy n8n workflow ${LEGACY_ID}.`);
  } finally {
    await client.end();
  }
}

main().catch((error) => {
  console.error(error.message);
  process.exitCode = 1;
});
