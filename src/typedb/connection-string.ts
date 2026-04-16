/**
 * Parses TypeDB Cloud / driver-style `typedb://…` connection strings for the HTTP driver.
 *
 * Example:
 * `typedb://admin:secret@https://cluster.example.com:443/?name=mydb`
 * → addresses `["https://cluster.example.com:443"]`, optional username/password, optional DB name from `name=`.
 */

export type ParsedTypeDbConnectionString = {
  addresses: string[];
  username?: string;
  password?: string;
  /** `name` query parameter when present */
  databaseFromQuery?: string;
};

/**
 * @returns `undefined` if `raw` is empty or not a `typedb://` URI we recognise.
 */
export function parseTypeDbConnectionString(raw: string): ParsedTypeDbConnectionString | undefined {
  const s = raw.trim();
  if (!s || !s.toLowerCase().startsWith("typedb://")) {
    return undefined;
  }

  const withoutScheme = s.slice("typedb://".length);
  let user: string | undefined;
  let password: string | undefined;
  let hostPart = withoutScheme;

  const atIdx = withoutScheme.indexOf("@");
  if (atIdx !== -1) {
    const auth = withoutScheme.slice(0, atIdx);
    hostPart = withoutScheme.slice(atIdx + 1);
    const colon = auth.indexOf(":");
    if (colon >= 0) {
      user = auth.slice(0, colon).trim() || undefined;
      password = auth.slice(colon + 1).trim() || undefined;
    } else {
      user = auth.trim() || undefined;
    }
  }

  const urlCandidate =
    hostPart.startsWith("http://") || hostPart.startsWith("https://") ? hostPart : `https://${hostPart}`;

  let url: URL;
  try {
    url = new URL(urlCandidate);
  } catch {
    throw new TypeError(`Invalid TYPEDB_CONNECTION_STRING (bad URL after @): ${JSON.stringify(hostPart)}`);
  }

  const addresses = [`${url.protocol}//${url.host}`];
  const nameRaw = url.searchParams.get("name")?.trim();
  const databaseFromQuery = nameRaw ? decodeURIComponent(nameRaw) : undefined;

  return {
    addresses,
    username: user,
    password,
    databaseFromQuery,
  };
}
