import {
  isApiErrorResponse,
  isOkResponse,
  type TypeDBHttpDriver,
} from "@typedb/driver-http";

/**
 * Opens a read transaction, runs `fn` with `transactionId`, then closes the transaction
 * in a `finally` block (driver best practice: always close).
 */
export async function withReadTransaction<T>(
  driver: TypeDBHttpDriver,
  databaseName: string,
  fn: (transactionId: string) => Promise<T>,
): Promise<T> {
  const open = await driver.openTransaction(databaseName, "read");
  if (isApiErrorResponse(open)) {
    throw new Error(`openTransaction failed: ${open.err.code} ${open.err.message}`);
  }
  if (!isOkResponse(open)) {
    throw new Error("openTransaction: unexpected response");
  }
  const transactionId = open.ok.transactionId;
  try {
    return await fn(transactionId);
  } finally {
    const close = await driver.closeTransaction(transactionId);
    if (isApiErrorResponse(close)) {
      // Best-effort close; server may have already ended the transaction.
    }
  }
}
