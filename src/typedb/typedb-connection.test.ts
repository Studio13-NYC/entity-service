import path from "node:path";

import { config } from "dotenv";
import { describe, expect, it } from "vitest";

import { readTypeDbEnvFromProcess } from "./env";
import { verifyTypeDbConnection } from "./verify-connection";

// Load repo-root `.env` before reading process.env (Node does not load .env automatically).
config({ path: path.join(process.cwd(), ".env") });

const typeDbEnv = readTypeDbEnvFromProcess();

describe("TypeDB HTTP integration", () => {
  it.skipIf(!typeDbEnv)(
    "connects with credentials from .env and can run a schema read",
    async () => {
      const result = await verifyTypeDbConnection(typeDbEnv!);

      expect(result.healthOk).toBe(true);
      expect(result.databaseNames).toContain(typeDbEnv!.database);
      expect(result.version).toBeTruthy();
    },
  );
});
