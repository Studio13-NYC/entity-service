"""Parse TypeDB ``define`` type-schema text (aligned with ``src/typedb/type-schema-define-parse.ts``)."""

from __future__ import annotations

import re


def parse_entity_type_labels_from_define_schema(define_body: str) -> list[str]:
    labels: set[str] = set()
    for m in re.finditer(r"\bentity\s+([A-Za-z][\w-]*)\b", define_body):
        labels.add(m.group(1))
    for m in re.finditer(r"\b([A-Za-z][\w-]*)\s+sub\s+entity\b", define_body):
        labels.add(m.group(1))
    return sorted(labels)


def _parse_attribute_types_value_string(define_body: str) -> set[str]:
    string_attrs: set[str] = set()
    for m in re.finditer(r"\battribute\s+([A-Za-z][\w-]*)\s*,\s*value\s+string\b", define_body):
        string_attrs.add(m.group(1))
    for m in re.finditer(
        r"\b([A-Za-z][\w-]*)\s+sub\s+attribute\b[\s\S]*?value\s+string\b",
        define_body,
    ):
        string_attrs.add(m.group(1))
    return string_attrs


def parse_string_attribute_types_owned_by_entity_from_define_schema(
    define_body: str,
    entity_type: str,
) -> list[str]:
    if not re.match(r"^[A-Za-z][A-Za-z0-9_-]*$", entity_type):
        raise ValueError(f"invalid entity type label: {entity_type!r}")
    string_attrs = _parse_attribute_types_value_string(define_body)
    block_m = re.search(rf"\bentity\s+{re.escape(entity_type)}\b([\s\S]*?);", define_body, re.MULTILINE)
    if not block_m:
        return []
    block = block_m.group(0)
    owned: set[str] = set()
    for m in re.finditer(r"\bowns\s+([A-Za-z][\w-]*)", block):
        owned.add(m.group(1))
    return sorted(a for a in owned if a in string_attrs)
