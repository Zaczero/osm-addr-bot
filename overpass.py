from itertools import chain

from check import Check
from config import SEARCH_BBOX, SEARCH_RELATION
from overpass_entry import OverpassEntry
from state import State
from utils import get_http_client, format_timestamp, parse_timestamp


def get_bbox() -> str:
    e = SEARCH_BBOX
    min_lat, max_lat = e['min_lat'], e['max_lat']
    min_lon, max_lon = e['min_lon'], e['max_lon']
    return f'[bbox:{min_lat},{min_lon},{max_lat},{max_lon}]'


def build_query(start_ts: int, end_ts: int, check: Check, timeout: int) -> str:
    assert start_ts < end_ts
    start = format_timestamp(start_ts)
    end = format_timestamp(end_ts)

    return f'[out:json][timeout:{timeout}]{get_bbox()};' \
           f'relation(id:{SEARCH_RELATION});map_to_area;' \
           f'(' \
           f'nwr{check.overpass}(changed:"{start}","{end}")(area._);' \
           f');' \
           f'out meta;'


def build_partition_query(timestamp: int, issues: list[OverpassEntry], timeout: int) -> str:
    date = format_timestamp(timestamp - 1)
    selector = ''.join(f'{i.element_type}(id:{i.element_id});' for i in issues)

    return f'[out:json][date:"{date}"][timeout:{timeout}]{get_bbox()};' \
           f'({selector});' \
           f'out meta;'


def build_duplicates_query(issues: list[OverpassEntry], timeout: int) -> str:
    body = ''.join(
        f'{i.element_type}(id:{i.element_id})->.a;'
        f'(nwr["addr:housenumber"](around.a:60)(if: t["addr:housenumber"] == "{i.tags["addr:housenumber"]}"); - .a;);'
        f'out tags;'
        f'.a out ids;'
        for i in issues)

    return f'[out:json][timeout:{timeout}]{get_bbox()};{body}'


def build_place_not_in_area_query(issues: list[OverpassEntry], timeout: int) -> str:
    body = ''.join(
        f'{i.element_type}(id:{i.element_id})->.a;'
        f'(.a;.a>;.a>>;);'
        f'is_in->.i;'
        f'('
        f'wr.i[!admin_level][name="{i.tags["addr:place"]}"];'
        f'area.i[!admin_level][name="{i.tags["addr:place"]}"];'
        f');'
        f'out tags;'
        f'.a out ids;'
        for i in issues)

    return f'[out:json][timeout:{timeout}]{get_bbox()};{body}'


class Overpass:
    def __init__(self, state: State):
        self.state = state

        self.base_url = 'https://overpass.monicz.dev/api/interpreter'
        self.c = get_http_client()

    def query(self, check: Check) -> list[OverpassEntry] | bool:
        timeout = 300
        query = build_query(self.state.start_ts, self.state.end_ts, check, timeout=timeout)

        r = self.c.post(self.base_url, data={'data': query}, timeout=timeout)
        r.raise_for_status()

        data = r.json()
        overpass_ts = parse_timestamp(data['osm3s']['timestamp_osm_base'])

        if self.state.end_ts >= overpass_ts:
            return False

        elements = data['elements']

        result = [
            r
            for r in (OverpassEntry(
                timestamp=e['timestamp'],
                changeset_id=e['changeset'],
                element_type=e['type'],
                element_id=e['id'],
                tags=e['tags'],
                reason=check
            ) for e in elements)
            if self.state.start_ts <= r.timestamp <= self.state.end_ts
        ]

        return result

    def query_duplicates(self, issues: list[OverpassEntry]) -> list[OverpassEntry]:
        whitelist_tags = (
            'addr:',
            'building',
            'capacity',
            'fixme',
            'height',
            'layer',
            'note',
            'source'
        )

        equal_tags = (
            'addr:city',
            'addr:place',
            'addr:street',
            # 'addr:housenumber' - checked in query
        )

        def check_whitelist(tags: dict) -> bool:
            return all(
                any(
                    t.startswith(w)
                    for w in whitelist_tags
                )
                for t in tags
            )

        def check_equal_tags(left: dict, right: dict, key: str) -> bool:
            return left.get(key, None) == right.get(key, None)

        valid_issues = [i for i in issues if check_whitelist(i.tags)]

        if not valid_issues:
            return []

        timeout = 300
        query = build_duplicates_query(valid_issues, timeout=timeout)

        r = self.c.post(self.base_url, data={'data': query}, timeout=timeout)
        r.raise_for_status()

        data = r.json()['elements']
        data_iter = iter(data)
        result = []

        for issue in valid_issues:
            duplicated = False

            for element in data_iter:
                # check for end of section
                if 'tags' not in element:
                    assert element['type'] == issue.element_type and element['id'] == issue.element_id
                    break

                if not all(check_equal_tags(element['tags'], issue.tags, t) for t in equal_tags):
                    continue

                if not check_whitelist(element['tags']):
                    continue

                duplicated = True

            if duplicated:
                result.append(issue)

        return result

    def query_place_not_in_area(self, issues: list[OverpassEntry]) -> list[OverpassEntry]:
        timeout = 300
        query = build_place_not_in_area_query(issues, timeout=timeout)

        r = self.c.post(self.base_url, data={'data': query}, timeout=timeout)
        r.raise_for_status()

        data = r.json()['elements']
        data_iter = iter(data)
        result = []

        for issue in issues:
            place_ok = False

            for element in data_iter:
                # check for end of section
                if 'tags' not in element:
                    assert element['type'] == issue.element_type and element['id'] == issue.element_id
                    break

                place_ok = True

            if not place_ok:
                result.append(issue)

        return result

    def is_editing_address(self, issues: dict[Check, list[OverpassEntry]]) -> bool:
        timeout = 300
        partitions: dict[int, list[OverpassEntry]] = {}
        issues_map: dict[str, dict[int, OverpassEntry]] = {}

        for issue in chain.from_iterable(issues.values()):
            partitions.setdefault(issue.timestamp, []).append(issue)
            issues_map.setdefault(issue.element_type, {})[issue.element_id] = issue

        for partition_time, partition_issues in partitions.items():
            partition_query = build_partition_query(partition_time, partition_issues, timeout=timeout)

            r = self.c.post(self.base_url, data={'data': partition_query}, timeout=timeout)
            r.raise_for_status()

            elements = r.json()['elements']

            # fewer elements means some were created
            if len(elements) < len(partition_issues):
                return True

            if len(elements) > len(partition_issues):
                raise

            for element in elements:
                ref_issue = issues_map[element['type']][element['id']]
                tags_diff = {k: v for k, v in set(ref_issue.tags.items()) - set(element.get('tags', {}).items())}

                if any(k.startswith('addr:') for k in tags_diff):
                    return True

        return False
