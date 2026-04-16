/**
 * Best-effort parsing of TypeDB `getDatabaseTypeSchema` / `define` output (TypeDB 2.x and 3.x shapes).
 * Used where TypeQL `sub entity` is not accepted (e.g. TypeDB 3 Cloud).
 */

import { assertSafeTypeqlIdentifier } from "./typeql-builders";

/** Labels declared as entity types in a `define` type schema string. */
export function parseEntityTypeLabelsFromDefineSchema(defineBody: string): string[] {
  const labels = new Set<string>();

  // TypeDB 3: `entity user, owns …` or `entity company,\n  sub organization;`
  const re3 = /\bentity\s+([A-Za-z][\w-]*)\b/g;
  let m: RegExpExecArray | null;
  while ((m = re3.exec(defineBody)) !== null) {
    labels.add(m[1]);
  }

  // TypeDB 2 style: `person sub entity`
  const re2 = /\b([A-Za-z][\w-]*)\s+sub\s+entity\b/g;
  while ((m = re2.exec(defineBody)) !== null) {
    labels.add(m[1]);
  }

  return [...labels].sort();
}

function parseAttributeTypesWithValueString(defineBody: string): Set<string> {
  const stringAttrs = new Set<string>();
  // `attribute username, value string` (TypeDB 3)
  const re3 = /\battribute\s+([A-Za-z][\w-]*)\s*,\s*value\s+string\b/g;
  let m: RegExpExecArray | null;
  while ((m = re3.exec(defineBody)) !== null) {
    stringAttrs.add(m[1]);
  }
  // `full-name sub attribute, value string` (2.x-ish)
  const re2 = /\b([A-Za-z][\w-]*)\s+sub\s+attribute\b[\s\S]*?value\s+string\b/g;
  while ((m = re2.exec(defineBody)) !== null) {
    stringAttrs.add(m[1]);
  }
  return stringAttrs;
}

/**
 * Attribute type labels with `value string` that appear in an `entity <name> … owns …` block.
 */
export function parseStringAttributeTypesOwnedByEntityFromDefineSchema(
  defineBody: string,
  entityType: string,
): string[] {
  assertSafeTypeqlIdentifier(entityType, "entityType");
  const stringAttrs = parseAttributeTypesWithValueString(defineBody);

  const blockRe = new RegExp(`\\bentity\\s+${entityType}\\b([\\s\\S]*?);`, "m");
  const blockMatch = defineBody.match(blockRe);
  if (!blockMatch) {
    return [];
  }
  const block = blockMatch[0];
  const owned = new Set<string>();
  const ownsRe = /\bowns\s+([A-Za-z][\w-]*)/g;
  let om: RegExpExecArray | null;
  while ((om = ownsRe.exec(block)) !== null) {
    owned.add(om[1]);
  }

  return [...owned].filter((a) => stringAttrs.has(a)).sort();
}
