import type { Attribute, ConceptRow, Entity } from "@typedb/driver-http";

/**
 * Validates one `select` row from a data (`read`) query against TypeDB's type-centric model:
 * instances carry **typed** `entity.type` / `attribute.type` metadata when `includeInstanceTypes` is enabled.
 *
 * @returns canonical string value and the **instance** entity type label (`entity.type.label`), or `null` if the row is not a valid entity+string-attribute projection.
 */
export function parseValidatedEntityStringAttributeRow(
  row: ConceptRow,
  expectedAttributeTypeLabel: string,
): { instanceEntityTypeLabel: string; value: string } | null {
  let entity: Entity | undefined;
  let attr: Attribute | undefined;
  for (const c of Object.values(row)) {
    if (!c) continue;
    if (c.kind === "entity") {
      entity = c;
    } else if (c.kind === "attribute") {
      attr = c;
    }
  }
  if (!entity || !attr) {
    return null;
  }
  if (entity.type.kind !== "entityType") {
    return null;
  }
  if (attr.type.kind !== "attributeType") {
    return null;
  }
  if (attr.type.valueType !== "string") {
    return null;
  }
  if (attr.type.label !== expectedAttributeTypeLabel) {
    return null;
  }
  return {
    instanceEntityTypeLabel: entity.type.label,
    value: String(attr.value),
  };
}
