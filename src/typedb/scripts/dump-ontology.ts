/**
 * One-off: print type-schema snippet and parsed entity labels (requires TYPEDB_* or TYPEDB_CONNECTION_STRING in `.env`).
 * Run: npx ts-node src/typedb/scripts/dump-ontology.ts
 */
import path from "node:path";

import { isApiErrorResponse, isOkResponse } from "@typedb/driver-http";
import { config } from "dotenv";

import { createTypeDbDriver } from "../driver-factory";
import { readTypeDbEnvFromProcess } from "../env";
import { parseEntityTypeLabelsFromDefineSchema } from "../type-schema-define-parse";

config({ path: path.join(process.cwd(), ".env") });

async function main(): Promise<void> {
  const env = readTypeDbEnvFromProcess();
  if (!env) {
    console.error(
      "Set TYPEDB_CONNECTION_STRING or TYPEDB_USERNAME + TYPEDB_DATABASE (+ optional TYPEDB_ADDRESSES, TYPEDB_PASSWORD).",
    );
    process.exit(1);
  }
  const driver = createTypeDbDriver(env);
  const db = env.database;

  const typeSchema = await driver.getDatabaseTypeSchema(db);
  if (isApiErrorResponse(typeSchema)) {
    console.error("getDatabaseTypeSchema", typeSchema.err);
    process.exit(1);
  }
  if (!isOkResponse(typeSchema)) {
    console.error("getDatabaseTypeSchema: unexpected response");
    process.exit(1);
  }
  const s = typeSchema.ok;
  console.log("--- type-schema (first 1200 chars) ---\n", s.slice(0, 1200));
  const labels = parseEntityTypeLabelsFromDefineSchema(s);
  console.log("\n--- parsed entity type labels (count %d) ---\n", labels.length);
  console.log(labels.join(", "));
}

void main();
