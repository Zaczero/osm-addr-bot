from itertools import chain
from pprint import pprint

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


def build_query(start_ts: int, end_ts: int, checks: list[Check], timeout: int) -> str:
    assert start_ts < end_ts
    start = format_timestamp(start_ts)
    end = format_timestamp(end_ts)
    body = ''.join(
        (f'{c.overpass};' if c.overpass_raw else f'nwr{c.overpass}(changed:"{start}","{end}")(area.a);') +
        f'out meta;'
        f'out count;'
        for c in checks)

    return f'[out:json][timeout:{timeout}]{get_bbox()};' \
           f'relation(id:{SEARCH_RELATION});' \
           f'map_to_area->.a;' \
           f'nwr["addr:housenumber"](changed:"{start}","{end}")(area.a)->.h;' \
           f'nwr["addr:place"](changed:"{start}","{end}")(area.a)->.p;' \
           f'nwr["addr:street"](changed:"{start}","{end}")(area.a)->.s;' \
           f'{body}'


def build_partition_query(timestamp: int, issues: list[OverpassEntry], timeout: int) -> str:
    date = format_timestamp(timestamp - 1)
    selector = ''.join(f'{i.element_type}(id:{i.element_id});' for i in issues)

    return f'[out:json][date:"{date}"][timeout:{timeout}]{get_bbox()};' \
           f'({selector});' \
           f'out meta;'


def build_duplicates_query(issues: list[OverpassEntry], timeout: int) -> str:
    body = ''.join(
        f'{i.element_type}(id:{i.element_id})->.a;'
        f'('
        f'nwr["addr:housenumber"](around.a:100)(if: t["addr:housenumber"] == "{i.tags["addr:housenumber"]}"); - '
        f'{i.element_type}["addr:housenumber"](around.a:0);'
        f');'
        f'out tags;'
        f'.a out ids;'
        for i in issues)

    return f'[out:json][timeout:{timeout}]{get_bbox()};{body}'


def build_place_not_in_area_query(issues: list[OverpassEntry], timeout: int) -> str:
    body = ''.join(
        f'{i.element_type}(id:{i.element_id});' +
        ('' if i.element_type == 'node' else f'node({i.element_type[0]});') +
        f'is_in;'
        f'wr._[!admin_level][name];'
        f'out tags;'
        f'out count;'
        for i in issues)

    return f'[out:json][timeout:{timeout}]{get_bbox()};{body}'


def build_street_names_query(issues: list[OverpassEntry], timeout: int) -> str:
    body = ''.join(
        f'{i.element_type}(id:{i.element_id})->.a;'
        f'wr[highway][name="{i.tags["addr:street"]}"](around.a:500);'
        f'out tags;'
        f'.a out ids;'
        for i in issues)

    return f'[out:json][timeout:{timeout}]{get_bbox()};{body}'


class Overpass:
    def __init__(self, state: State):
        self.state = state

        self.base_url = 'https://overpass.monicz.dev/api/interpreter'
        self.c = get_http_client()

    def query(self, checks: list[Check]) -> dict[Check, list[OverpassEntry]] | bool:
        timeout = 300
        query = build_query(self.state.start_ts, self.state.end_ts, checks, timeout=timeout)

        r = self.c.post(self.base_url, data={'data': query}, timeout=timeout)
        r.raise_for_status()

        data = r.json()
        overpass_ts = parse_timestamp(data['osm3s']['timestamp_osm_base'])

        if self.state.end_ts >= overpass_ts:
            return False

        data = r.json()['elements']
        data_iter = iter(data)
        result = {}

        for check in checks:
            result[check] = check_list = []
            return_size = 0

            for e in data_iter:
                # check for end of section
                if e['type'] == 'count':
                    assert int(e['tags']['total']) == return_size
                    break

                return_size += 1

                entry = OverpassEntry(
                    timestamp=e['timestamp'],
                    changeset_id=e['changeset'],
                    element_type=e['type'],
                    element_id=e['id'],
                    tags=e['tags']
                )

                if self.state.start_ts <= entry.timestamp <= self.state.end_ts:
                    check_list.append(entry)
            else:
                raise

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
            else:
                raise

            if duplicated:
                result.append(issue)

        return result

    def query_place_not_in_area(self, issues: list[OverpassEntry], mistype_mode: bool) -> list[OverpassEntry]:
        timeout = 300
        query = build_place_not_in_area_query(issues, timeout=timeout)

        r = self.c.post(self.base_url, data={'data': query}, timeout=timeout)
        r.raise_for_status()

        data = r.json()['elements']
        data_iter = iter(data)
        result = []

        for issue in issues:
            is_in = set()

            for e in data_iter:
                # check for end of section
                if e['type'] == 'count':
                    assert int(e['tags']['total']) == len(is_in)
                    break

                is_in.add(e['tags']['name'])
            else:
                raise

            place_ok = issue.tags['addr:place'] in is_in

            # place_ok <=> addr:place is ( valid OR not mistype )
            if not place_ok and mistype_mode:
                addr_place_alt = issue.tags['addr:place'].strip().lower()
                is_in_mistype = any(addr_place_alt == i.strip().lower() for i in is_in)
                place_ok = not is_in_mistype

                if not place_ok:
                    print(is_in_mistype)
                    pprint(issue.tags)
                    pprint(is_in)

            if not place_ok:
                result.append(issue)

        return result

    def query_street_names(self, issues: list[OverpassEntry]) -> list[OverpassEntry]:
        timeout = 300
        query = build_street_names_query(issues, timeout=timeout)

        r = self.c.post(self.base_url, data={'data': query}, timeout=timeout)
        r.raise_for_status()

        data = r.json()['elements']
        data_iter = iter(data)
        result = []

        for issue in issues:
            street_ok = False

            for element in data_iter:
                # check for end of section
                if 'tags' not in element:
                    assert element['type'] == issue.element_type and element['id'] == issue.element_id
                    break

                street_ok = True
            else:
                raise

            if not street_ok:
                result.append(issue)

        return result

    def is_editing_address(self, issues: dict[Check, list[OverpassEntry]]) -> bool:
        timeout = 300
        partitions: dict[int, set[OverpassEntry]] = {}
        entry_map: dict[str, dict[int, OverpassEntry]] = {}

        for entry in chain.from_iterable(issues.values()):
            partitions.setdefault(entry.timestamp, set()).add(entry)
            entry_map.setdefault(entry.element_type, {})[entry.element_id] = entry

        for partition_time, partition_issues in partitions.items():
            partition_query = build_partition_query(partition_time, list(partition_issues), timeout=timeout)

            r = self.c.post(self.base_url, data={'data': partition_query}, timeout=timeout)
            r.raise_for_status()

            elements = r.json()['elements']

            # fewer elements means some were created
            if len(elements) < len(partition_issues):
                return True

            if len(elements) > len(partition_issues):
                raise

            for element in elements:
                ref_entry = entry_map[element['type']][element['id']]
                tags_diff = {k: v for k, v in set(ref_entry.tags.items()) - set(element.get('tags', {}).items())}

                if any(k.startswith('addr:') for k in tags_diff):
                    return True

        return False
