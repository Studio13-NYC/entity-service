import { TypeDBHttpDriver } from "@typedb/driver-http";

import type { TypeDbEnv } from "./env";

/**
 * Creates a TypeDB HTTP driver. Prefer a single long-lived driver per process and
 * short-lived read transactions (or `oneShotQuery`) per request.
 */
export function createTypeDbDriver(env: TypeDbEnv): TypeDBHttpDriver {
  return new TypeDBHttpDriver({
    username: env.username,
    password: env.password,
    addresses: env.addresses,
  });
}
