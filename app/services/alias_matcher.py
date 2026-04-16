from collections.abc import Sequence
from dataclasses import dataclass

from app.config.aliases import ALIASES, AliasRow


@dataclass(frozen=True)
class AliasMatch:
    canonical_text: str
    label: str
    alias_text: str
    start: int
    end: int
    confidence: float = 0.98


class AliasMatcher:
    """Per-request alias table: default config rows plus optional runtime rows."""

    __slots__ = ("_rows",)

    def __init__(self, rows: Sequence[AliasRow]) -> None:
        self._rows: list[AliasRow] = list(rows)

    def find(self, text: str) -> list[AliasMatch]:
        matches: list[AliasMatch] = []
        for label, canonical_text, alias_text in self._rows:
            search_start = 0
            while True:
                index = text.find(alias_text, search_start)
                if index == -1:
                    break
                matches.append(
                    AliasMatch(
                        canonical_text=canonical_text,
                        label=label,
                        alias_text=alias_text,
                        start=index,
                        end=index + len(alias_text),
                    ),
                )
                search_start = index + 1
        return _dedupe_matches(matches)


def find_alias_matches(
    text: str,
    extra_aliases: Sequence[AliasRow] | None = None,
) -> list[AliasMatch]:
    """Match using bundled default aliases plus optional runtime rows from schema."""
    rows: list[AliasRow] = [*ALIASES]
    if extra_aliases:
        rows.extend(extra_aliases)
    return AliasMatcher(rows).find(text)


def _dedupe_matches(matches: list[AliasMatch]) -> list[AliasMatch]:
    if not matches:
        return []

    sorted_matches = sorted(
        matches,
        key=lambda m: (
            m.start,
            -(m.end - m.start),
            m.label,
            m.canonical_text,
        ),
    )

    deduped: list[AliasMatch] = []

    for match in sorted_matches:
        overlaps_existing = any(
            not (match.end <= existing.start or match.start >= existing.end)
            and match.label == existing.label
            for existing in deduped
        )

        if not overlaps_existing:
            deduped.append(match)

    return deduped
