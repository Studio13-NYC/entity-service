"""Safe TypeQL fragments (aligned with ``src/typedb/typeql-builders.ts``)."""

from __future__ import annotations

import re

_SAFE = re.compile(r"^[A-Za-z][A-Za-z0-9_-]*$")


def assert_safe_typeql_identifier(label: str, field_name: str) -> None:
    if not _SAFE.match(label):
        raise ValueError(
            f"{field_name} must match {_SAFE.pattern} to prevent TypeQL injection; got {label!r}",
        )


def build_select_entity_with_string_attribute(entity_type: str, attribute_name: str) -> str:
    assert_safe_typeql_identifier(entity_type, "entityType")
    assert_safe_typeql_identifier(attribute_name, "attributeName")
    return (
        "match\n"
        f"  $e isa {entity_type},\n"
        f"  has {attribute_name} $v;\n"
        "select $e, $v;\n"
    )
