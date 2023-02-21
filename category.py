from collections import defaultdict
from dataclasses import dataclass, field
from typing import Callable

from aliases import Identifier, Tags
from check import Check
from overpass_entry import OverpassEntry


@dataclass(frozen=True, kw_only=True, slots=True)
class Category:
    identifier: Identifier
    header_critical: str
    header: str
    docs: str | None
    pre_fn: Callable[[Tags], bool]
    edit_tags: tuple[str, ...] = tuple()
    checks: list[Check]

    def map_checks(self, entries: list[OverpassEntry]) -> dict[Check, list[OverpassEntry]]:
        result = defaultdict(list)

        for e in entries:
            if self.pre_fn(e.tags):
                for c in self.checks:
                    if c.pre_fn(e.tags):
                        result[c].append(e)

        return result
