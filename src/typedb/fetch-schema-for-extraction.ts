import {
  isApiErrorResponse,
  isOkResponse,
  type ConceptRowsQueryResponse,
  type TypeDBHttpDriver,
} from "@typedb/driver-http";

import { assertExtractionPlanInOntology } from "./introspect-ontology";
import { buildSelectEntityWithStringAttribute } from "./typeql-builders";
import type { TypeDbKnownEntity, TypeDbSchemaSnapshot } from "./schema-adapter";
import { parseValidatedEntityStringAttributeRow } from "./validate-data-concepts";

export type FetchSchemaForExtractionOptions = {
  /** Max rows per entity-type query (answerCountLimit — keeps reads bounded). */
  limitPerType?: number;
  /** TypeDB entity type labels to scan (e.g. `person`, `recording`). */
  entityTypes: string[];
  /** Attribute used as canonical display string for extraction (default `name`). */
  nameAttribute?: string;
  /** Optional transaction timeout for one-shot reads (ms). */
  transactionTimeoutMillis?: number;
  /**
   * When true (default), load the live type graph and ensure each `entityTypes[]` entry exists and
   * {@link nameAttribute} is a declared string attribute on that type (`owns`).
   */
  validateOntology?: boolean;
};

function assertConceptRows(
  res: unknown,
  context: string,
): asserts res is ConceptRowsQueryResponse {
  if (!res || typeof res !== "object") {
    throw new TypeError(`${context}: invalid query response`);
  }
  const r = res as ConceptRowsQueryResponse;
  if (r.answerType !== "conceptRows") {
    throw new Error(`${context}: expected conceptRows, got ${(r as { answerType?: string }).answerType}`);
  }
}

/**
 * Runs bounded TypeQL `match` + `select` reads per entity type and builds a snapshot for
 * {@link toEntitySchemaPayload}. Uses `oneShotQuery` (read, no commit) so transactions stay short.
 *
 * Does not call the NER HTTP service — compose with `NerServiceClient.extract` in your app.
 */
export async function fetchSchemaForExtraction(
  driver: TypeDBHttpDriver,
  databaseName: string,
  options: FetchSchemaForExtractionOptions,
): Promise<TypeDbSchemaSnapshot> {
  const nameAttr = options.nameAttribute ?? "name";
  const limit = options.limitPerType ?? 500;
  const timeout = options.transactionTimeoutMillis ?? 30_000;
  const validateOntology = options.validateOntology !== false;

  if (validateOntology) {
    await assertExtractionPlanInOntology(driver, databaseName, {
      entityTypes: options.entityTypes,
      nameAttribute: nameAttr,
    });
  }

  const knownEntities: TypeDbKnownEntity[] = [];

  for (const entityType of options.entityTypes) {
    const typeql = buildSelectEntityWithStringAttribute(entityType, nameAttr);
    const res = await driver.oneShotQuery(
      typeql,
      false,
      databaseName,
      "read",
      { transactionTimeoutMillis: timeout },
      {
        answerCountLimit: limit,
        includeInstanceTypes: true,
      },
    );

    if (isApiErrorResponse(res)) {
      throw new Error(`TypeDB query failed for type ${entityType}: ${res.err.code} ${res.err.message}`);
    }
    if (!isOkResponse(res)) {
      throw new Error(`TypeDB unexpected response for type ${entityType}`);
    }

    assertConceptRows(res.ok, `TypeDB ${entityType}`);

    for (const answer of res.ok.answers) {
      const parsed = parseValidatedEntityStringAttributeRow(answer.data, nameAttr);
      if (!parsed) continue;
      // Use the requested query bucket as `typeId` so `labels` / client vocabulary stay aligned;
      // ontology is enforced by `assertExtractionPlanInOntology` + typed concept checks above.
      knownEntities.push({
        typeId: entityType,
        canonicalName: parsed.value,
        aliases: [],
      });
    }
  }

  const entityTypes = options.entityTypes.map((id) => ({ id }));

  return { entityTypes, knownEntities };
}
