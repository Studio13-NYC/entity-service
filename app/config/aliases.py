"""Default alias catalog: nested dict + flattened rows for the matcher.

Structure: ``{ entity_label: { canonical_surface: [alias_substrings...] } }``.
This service does not load from a database; aliases are static config here plus
optional runtime rows from the client ``schema`` field.
"""

from typing import TypeAlias

AliasRow: TypeAlias = tuple[str, str, str]

ALIASES_NESTED: dict[str, dict[str, list[str]]] = {
    "artist": {
        "Matthew Sweet": [
            "Matthew Sweet",
            "Mathew Sweet",
            "Matt Sweet",
        ],
    },
    "recording": {
        "Girlfriend": [
            "Girlfriend",
            "girlfriend",
        ],
    },
    # Music Ontology–style TypeQL labels (hyphenated) are first-class bucket names for ``label`` / ``labels``.
    # Keep surfaces disjoint from ``artist`` / ``recording`` rows to avoid duplicate spans under different labels.
    "mo-test-widget": {
        "Widget Company": [
            "Widget Company",
            "Widget Co",
            "Widget",
        ],
    },
}


def nested_aliases_to_rows(nested: dict[str, dict[str, list[str]]]) -> list[AliasRow]:
    rows: list[AliasRow] = []
    for label, canonical_map in nested.items():
        for canonical, surfaces in canonical_map.items():
            for surface in surfaces:
                rows.append((label, canonical, surface))
    return rows


ALIASES: list[AliasRow] = nested_aliases_to_rows(ALIASES_NESTED)
