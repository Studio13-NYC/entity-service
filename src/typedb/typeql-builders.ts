/**
 * TypeQL fragments for bounded reads. Follows predicate-pushdown: constrain type + attribute
 * in the `match` before `select` (see TypeDB TypeQL optimisation guides).
 */

const SAFE_LABEL = /^[A-Za-z][A-Za-z0-9_-]*$/;

export function assertSafeTypeqlIdentifier(label: string, fieldName: string): void {
  if (!SAFE_LABEL.test(label)) {
    throw new TypeError(
      `${fieldName} must match ${SAFE_LABEL.source} to prevent TypeQL injection: got ${JSON.stringify(label)}`,
    );
  }
}

/**
 * Match entities of a concrete type that own a string attribute, then project entity + value.
 * Uses `isa` so subtypes are included (use `isa!` in schema if you need exact type only).
 */
export function buildSelectEntityWithStringAttribute(
  entityType: string,
  attributeName: string,
): string {
  assertSafeTypeqlIdentifier(entityType, "entityType");
  assertSafeTypeqlIdentifier(attributeName, "attributeName");
  return `match
  $e isa ${entityType},
  has ${attributeName} $v;
select $e, $v;
`;
}
