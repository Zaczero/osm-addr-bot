from collections import defaultdict, deque
from itertools import combinations

from aliases import Tags
from config import DUPLICATE_BFS_EXCLUDE_ADDR, DUPLICATE_FALSE_POSITIVE_MAX_DIST
from overpass_entry import OverpassEntry

WHITELIST_TAGS = (
    'addr:',
    'building',
    'capacity',
    'check_date',
    'construction',
    'fixme',
    'height',
    'layer',
    'name',
    'note',
    'proposed',
    'roof',
    'source',
    'start_date'
)

EQUAL_TAGS = (
    'addr:city',
    'addr:housenumber',
    'addr:place',
    'addr:street',
    'addr:unit'
)


def check_whitelist(tags: Tags) -> bool:
    return all(
        any(
            t.startswith(w)
            for w in WHITELIST_TAGS
        )
        for t in tags
    )


def check_equal_tag(left: Tags, right: Tags, key: str) -> bool:
    return left.get(key, None) == right.get(key, None)


def check_equal_tags(left: OverpassEntry, right: OverpassEntry) -> bool:
    return all(check_equal_tag(left.tags, right.tags, t) for t in EQUAL_TAGS)


def duplicate_search(entry: OverpassEntry,
                     ref_n: list[OverpassEntry], ref_wr: list[OverpassEntry]) -> list[OverpassEntry]:
    assert 'addr:housenumber' in entry.tags

    result = [
        e for e in ref_n
        if e != entry
           and check_whitelist(e.tags)
           and check_equal_tags(e, entry)
    ]

    wr_search_target = [
        e for e in ref_wr
        if e != entry
           and check_whitelist(e.tags)
           and check_equal_tags(e, entry)
    ]

    # for now assume all relations are valid matches (simplicity)
    for e in list(e for e in wr_search_target if e.element_type == 'relation'):
        wr_search_target.remove(e)
        result.append(e)

    if not wr_search_target:
        return result

    def build_graph(data: list[OverpassEntry]) -> dict[OverpassEntry, list[OverpassEntry]]:
        g = defaultdict(list)

        for e1, e2 in combinations(data, 2):
            if any(n1 in e2.nodes for n1 in e1.nodes):
                g[e1].append(e2)
                g[e2].append(e1)

        return g

    graph = build_graph(ref_wr)

    def bfs(start: OverpassEntry, end: OverpassEntry) -> int:
        visited = set()
        queue = deque()
        queue.append((start, 0))

        while queue:
            e, dist = queue.popleft()

            if e in visited:
                continue

            if e == end:
                return dist

            # abort further search, it's a duplicate
            if dist > DUPLICATE_FALSE_POSITIVE_MAX_DIST:
                return dist

            visited.add(e)

            # optionally, don't jump over elements with an address
            if DUPLICATE_BFS_EXCLUDE_ADDR and dist > 0 and 'addr:housenumber' in e.tags:
                continue

            for neighbor in graph[e]:
                queue.append((neighbor, dist + 1))

        # disconnected, it's a duplicate
        return -1

    for target in wr_search_target:
        target_dist = bfs(entry, target)

        if target_dist == -1 or target_dist > DUPLICATE_FALSE_POSITIVE_MAX_DIST:
            result.append(target)

    return result
