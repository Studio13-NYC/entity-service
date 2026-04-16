import { isApiErrorResponse, isOkResponse, type TypeDBHttpDriver } from "@typedb/driver-http";

import { assertSafeTypeqlIdentifier } from "./typeql-builders";
import {
  parseEntityTypeLabelsFromDefineSchema,
  parseStringAttributeTypesOwnedByEntityFromDefineSchema,
} from "./type-schema-define-parse";

export type ExtractionOntologyPlan = {
  entityTypes: readonly string[];
  nameAttribute: string;
};

/**
 * Raw TypeQL `define` string for the database type graph.
 */
export async function fetchTypeSchemaDefineString(
  driver: TypeDBHttpDriver,
  databaseName: string,
): Promise<string> {
  const res = await driver.getDatabaseTypeSchema(databaseName);
  if (isApiErrorResponse(res)) {
    throw new Error(`getDatabaseTypeSchema: ${res.err.code} ${res.err.message}`);
  }
  if (!isOkResponse(res)) {
    throw new Error("getDatabaseTypeSchema: unexpected response");
  }
  return res.ok;
}

/**
 * Entity type labels from the live **define** type schema (TypeDB 2.x / 3.x), without TypeQL `sub entity`
 * (not supported the same way on all TypeDB 3 deployments).
 */
export async function listEntityTypeLabels(
  driver: TypeDBHttpDriver,
  databaseName: string,
): Promise<readonly string[]> {
  const defineBody = await fetchTypeSchemaDefineString(driver, databaseName);
  return parseEntityTypeLabelsFromDefineSchema(defineBody);
}

/**
 * String-valued attribute types owned by `entityType`, inferred from the **define** schema text.
 */
export async function listStringAttributeTypeLabelsOwnedByEntityType(
  driver: TypeDBHttpDriver,
  databaseName: string,
  entityType: string,
): Promise<readonly string[]> {
  assertSafeTypeqlIdentifier(entityType, "entityType");
  const defineBody = await fetchTypeSchemaDefineString(driver, databaseName);
  return parseStringAttributeTypesOwnedByEntityFromDefineSchema(defineBody, entityType);
}

/**
 * Ensures each requested entity type exists in the live type graph and declares ownership of the
 * given string attribute type — grounded in the **define** ontology, not ad hoc TypeQL.
 */
export async function assertExtractionPlanInOntology(
  driver: TypeDBHttpDriver,
  databaseName: string,
  plan: ExtractionOntologyPlan,
): Promise<void> {
  assertSafeTypeqlIdentifier(plan.nameAttribute, "nameAttribute");
  const defineBody = await fetchTypeSchemaDefineString(driver, databaseName);
  const entityLabels = new Set(parseEntityTypeLabelsFromDefineSchema(defineBody));

  for (const et of plan.entityTypes) {
    assertSafeTypeqlIdentifier(et, "entityTypes[]");
    if (!entityLabels.has(et)) {
      const sample = [...entityLabels].slice(0, 40).join(", ");
      throw new Error(
        `Ontology: entity type ${JSON.stringify(et)} is not declared in the type schema. ` +
          `Sample labels: ${sample}${entityLabels.size > 40 ? ", …" : ""}`,
      );
    }
    const owns = new Set(parseStringAttributeTypesOwnedByEntityFromDefineSchema(defineBody, et));
    if (!owns.has(plan.nameAttribute)) {
      throw new Error(
        `Ontology: entity type ${JSON.stringify(et)} does not own string attribute ${JSON.stringify(plan.nameAttribute)}. ` +
          `Parsed string-valued owns: ${[...owns].join(", ") || "(none)"}`,
      );
    }
  }
}
