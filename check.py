from collections import defaultdict
from dataclasses import dataclass
from typing import TYPE_CHECKING, Callable, Iterable

from check_base import CheckBase

from aliases import Tags
from overpass_entry import OverpassEntry

if TYPE_CHECKING:
    from overpass import Overpass


@dataclass(frozen=True, kw_only=True, slots=True)
class Check(CheckBase):
    priority: int = 50
    critical: bool
    desc: str
    extra: str | None
    docs: str | None

    pre_fn: Callable[[Tags], bool] | None = None
    post_fn: Callable[['Overpass', list[OverpassEntry]], list[OverpassEntry]] | None = None

    def map_title_entries(self, entries: Iterable[OverpassEntry]) -> dict[str, list[OverpassEntry]]:
        result = defaultdict(list)

        # Group streets by name only if there are at least 3 entries
        if self.identifier == 'UNKNOWN_STREET_NAME' and len(entries) >= 3:
            for e in entries:
                result[f'"{e.tags["addr:street"]}":'].append(e)

        else:
            result[''] = entries

        assert ('' in result and len(result) == 1) or ('' not in result)
        return result
