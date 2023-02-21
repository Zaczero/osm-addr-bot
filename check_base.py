from dataclasses import dataclass
from fnmatch import fnmatch
from functools import cache

from aliases import Identifier, Selectors, Tags


@cache
def group_selectors(selectors: Selectors) -> tuple[Selectors, Selectors]:
    static_selectors = []
    dynamic_selectors = []

    for s in selectors:
        if '*' in s:
            dynamic_selectors.append(s)
        else:
            static_selectors.append(s)

    return tuple(static_selectors), tuple(dynamic_selectors)


@dataclass(frozen=True, kw_only=True, slots=True)
class CheckBase:
    identifier: Identifier
    selectors: Selectors = tuple()

    def is_selected(self, tags: Tags) -> bool:
        if not self.selectors:
            return False

        static_selectors, dynamic_selectors = group_selectors(self.selectors)

        return \
            all(s in tags for s in static_selectors) and \
            all(any(fnmatch(k, s) for k in tags) for s in dynamic_selectors)
