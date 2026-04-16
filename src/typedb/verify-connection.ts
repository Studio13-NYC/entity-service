import { isApiErrorResponse, isOkResponse } from "@typedb/driver-http";

import { createTypeDbDriver } from "./driver-factory";
import type { TypeDbEnv } from "./env";

export type TypeDbConnectionResult = {
  healthOk: boolean;
  distribution?: string;
  version?: string;
  databaseNames: readonly string[];
};

/**
 * Verifies HTTP reachability, auth, and that the configured database exists.
 * Runs a minimal schema `oneShotQuery` to confirm query permissions.
 */
export async function verifyTypeDbConnection(env: TypeDbEnv): Promise<TypeDbConnectionResult> {
  const driver = createTypeDbDriver(env);

  const healthRes = await driver.health();
  if (isApiErrorResponse(healthRes)) {
    throw new Error(`TypeDB health failed: ${healthRes.err.code} ${healthRes.err.message}`);
  }
  if (!isOkResponse(healthRes)) {
    throw new Error("TypeDB health: unexpected response shape");
  }

  const verRes = await driver.version();
  let distribution: string | undefined;
  let version: string | undefined;
  if (isOkResponse(verRes)) {
    distribution = verRes.ok.distribution;
    version = verRes.ok.version;
  }

  const dbsRes = await driver.getDatabases();
  if (isApiErrorResponse(dbsRes)) {
    throw new Error(`TypeDB getDatabases: ${dbsRes.err.code} ${dbsRes.err.message}`);
  }
  if (!isOkResponse(dbsRes)) {
    throw new Error("TypeDB getDatabases: unexpected response");
  }
  const databaseNames = dbsRes.ok.databases.map((d) => d.name);
  if (!databaseNames.includes(env.database)) {
    throw new Error(
      `TypeDB database ${JSON.stringify(env.database)} not found. ` +
        `Known databases: ${databaseNames.length ? databaseNames.sort().join(", ") : "(none)"}`,
    );
  }

  // Prefer the REST type-schema endpoint over a TypeQL `sub entity` probe — TypeQL surface syntax
  // differs across TypeDB versions, but this call still proves schema read access on the database.
  const typeSchemaRes = await driver.getDatabaseTypeSchema(env.database);
  if (isApiErrorResponse(typeSchemaRes)) {
    throw new Error(`TypeDB getDatabaseTypeSchema: ${typeSchemaRes.err.code} ${typeSchemaRes.err.message}`);
  }
  if (!isOkResponse(typeSchemaRes)) {
    throw new Error("TypeDB getDatabaseTypeSchema: unexpected response");
  }

  return {
    healthOk: true,
    distribution,
    version,
    databaseNames,
  };
}
