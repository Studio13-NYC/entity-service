/**
 * TypeDB connection settings from environment (never hardcode credentials in source).
 * @see https://typedb.com/docs/core-concepts/drivers/best-practices
 */

import { parseTypeDbConnectionString } from "./connection-string";

export type TypeDbEnv = {
  addresses: string[];
  username: string;
  password: string;
  database: string;
};

const DEFAULT_ADDRESSES = ["localhost:1729"];

/**
 * Reads TypeDB settings from the environment:
 *
 * - **`TYPEDB_CONNECTION_STRING`** (optional): `typedb://user:pass@https://host:port/?name=database`
 *   — supplies **addresses** (HTTP origin) and may supply username, password, and default database via `name=`.
 * - **`TYPEDB_ADDRESSES`** (optional): comma-separated origins or `host:port`; when set, overrides addresses from the connection string.
 * - **`TYPEDB_USERNAME`**, **`TYPEDB_PASSWORD`**, **`TYPEDB_DATABASE`**: explicit credentials; username/database required unless fully provided by the connection string.
 *
 * Values are **trimmed** so spaces after `=` in `.env` files do not break auth.
 */
export function readTypeDbEnvFromProcess(): TypeDbEnv | undefined {
  const connParsed = process.env.TYPEDB_CONNECTION_STRING?.trim()
    ? parseTypeDbConnectionString(process.env.TYPEDB_CONNECTION_STRING.trim())
    : undefined;

  const rawAddresses = process.env.TYPEDB_ADDRESSES?.trim();
  const addresses = rawAddresses
    ? rawAddresses.split(",").map((s) => s.trim()).filter(Boolean)
    : connParsed?.addresses?.length
      ? [...connParsed.addresses]
      : DEFAULT_ADDRESSES;

  const username =
    process.env.TYPEDB_USERNAME?.trim() || connParsed?.username?.trim() || undefined;
  const password = process.env.TYPEDB_PASSWORD?.trim() ?? connParsed?.password ?? "";
  const database =
    process.env.TYPEDB_DATABASE?.trim() || connParsed?.databaseFromQuery?.trim() || undefined;

  if (!username || !database) {
    return undefined;
  }
  return { addresses, username, password, database };
}
