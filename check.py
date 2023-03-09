from collections import defaultdict
from dataclasses import dataclass
from typing import Any, Callable, Iterable

from aliases import Tags
from check_base import CheckBase
from overpass_entry import OverpassEntry


@dataclass(frozen=True, kw_only=True, slots=True)
class Check(CheckBase):
    priority: int = 50
    critical: bool
    desc: str
    extra: str | None
    docs: str | None

    pre_fn: Callable[[Tags], bool] | None = None
    post_fn: Callable[[Any, list], list] | None = None

    def map_title_entries(self, entries: Iterable[OverpassEntry]) -> dict[str, list[OverpassEntry]]:
        result = defaultdict(list)

        if self.identifier == 'UNKNOWN_STREET_NAME' and len(entries) > 3:
            for e in entries:
                result[f'"{e.tags["addr:street"]}":'].append(e)

        else:
            result[''] = entries

        assert ('' in result and len(result) == 1) or ('' not in result)
        return result
