from dataclasses import dataclass
from typing import Iterable

from check import Check
from check_base import CheckBase
from overpass_entry import OverpassEntry


@dataclass(frozen=True, kw_only=True, slots=True)
class Category(CheckBase):
    header_critical: str
    header: str
    docs: str | None

    checks: tuple[Check, ...]

    def map_checks(self, entries: Iterable[OverpassEntry]) -> dict[Check, list[OverpassEntry]]:
        # filter with category selectors if set
        if self.selectors:
            entries = [e for e in entries if self.is_selected(e.tags)]

        result = {}

        for c in self.checks:
            if value := [e for e in entries if c.is_selected(e.tags) and (c.pre_fn is None or c.pre_fn(e.tags))]:
                result[c] = value

        return result
