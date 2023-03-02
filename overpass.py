from collections import defaultdict
from typing import Iterable

from geopy.distance import distance

from aliases import ElementType, Tags
from category import Category
from check import Check
from config import LARGE_ELEMENT_MAX_SIZE, SEARCH_BBOX, SEARCH_RELATION
from duplicate_search import check_whitelist, duplicate_search
from overpass_entry import OverpassEntry, Point, Size
from state import State
from utils import (escape_overpass, format_timestamp, get_http_client,
                   normalize, parse_timestamp)


def batch(size: int = 1000):
    def decorator(func):
        def wrapper(*args, **kwargs) -> list:
            assert len(args) >= 2 and isinstance(args[0], Overpass) and isinstance(args[1], list)

            self = args[0]
            task = args[1]
            result = []

            for subtask in (task[i:i + size] for i in range(0, len(task), size)):
                subtask_result = func(self, subtask, *args[2:], **kwargs)
                assert isinstance(subtask_result, list)
                result.extend(subtask_result)

            return result
        return wrapper
    return decorator


def tier(*tiers: Iterable[int]):
    def decorator(func):
        def wrapper(*args, **kwargs) -> list:
            assert len(args) >= 2 and isinstance(args[0], Overpass) and isinstance(args[1], list)

            self = args[0]
            task = args[1]

            for tier in tiers:
                if not task:
                    break

                task = func(self, task, *args[2:], **kwargs, tier=tier)
                assert isinstance(task, list)

            return task

        return wrapper
    return decorator


def skip_large(max_size: int = LARGE_ELEMENT_MAX_SIZE):
    def decorator(func):
        def wrapper(*args, **kwargs) -> list:
            assert len(args) >= 2 and isinstance(args[0], Overpass) and isinstance(args[1], list)

            self = args[0]
            task = args[1]

            task = [e for e in task if e.bb_size[0] < max_size and e.bb_size[1] < max_size]

            return func(self, task, *args[2:], **kwargs)
        return wrapper
    return decorator


def get_bbox() -> str:
    e = SEARCH_BBOX
    min_lat, max_lat = e['min_lat'], e['max_lat']
    min_lon, max_lon = e['min_lon'], e['max_lon']
    return f'[bbox:{min_lat},{min_lon},{max_lat},{max_lon}]'


def build_query(start_ts: int, end_ts: int, timeout: int) -> str:
    assert start_ts < end_ts
    start = format_timestamp(start_ts)
    end = format_timestamp(end_ts)

    return f'[out:json][timeout:{timeout}]{get_bbox()};' \
           f'relation(id:{SEARCH_RELATION});' \
           f'map_to_area;' \
           f'nwr(changed:"{start}","{end}")(area);' \
           f'out meta bb;'


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
        f'node["addr:housenumber"](around.a:100);' +
        (f'wr[building](around.a:100);' if i.element_type != 'node' else '') +
        f');'
        f'out body;'
        f'out count;'
        for i in issues)

    return f'[out:json][timeout:{timeout}]{get_bbox()};{body}'


def build_place_not_in_area_query(issues: list[OverpassEntry], timeout: int) -> str:
    body = ''.join(
        f'{i.element_type}(id:{i.element_id});'
        f'._->.a;' +
        ('' if i.element_type == 'node' else f'node({i.element_type[0]});') +
        f'is_in->.i;'
        f'('
        f'area.i[!admin_level][name="{escape_overpass(i.tags["addr:place"])}"];'
        f'wr.i[!admin_level][name="{escape_overpass(i.tags["addr:place"])}"];'
        f'node[place][name="{escape_overpass(i.tags["addr:place"])}"](around.a:10000);'
        f');'
        f'out tags;'
        f'out count;'
        for i in issues)

    return f'[out:json][timeout:{timeout}]{get_bbox()};{body}'


def build_place_mistype_query(issues: list[OverpassEntry], timeout: int) -> str:
    body = ''.join(
        f'{i.element_type}(id:{i.element_id});' +
        ('' if i.element_type == 'node' else f'node({i.element_type[0]});') +
        f'is_in;'
        f'wr._[!admin_level][name];'
        f'out tags;'
        f'out count;'
        for i in issues)

    return f'[out:json][timeout:{timeout}]{get_bbox()};{body}'


def build_street_names_query(issues: list[OverpassEntry], timeout: int, around: int) -> str:
    body = ''.join(
        f'{i.element_type}(id:{i.element_id});'
        f'wr[highway][name](around:{around});'
        f'out tags;'
        f'out count;'
        for i in issues)

    return f'[out:json][timeout:{timeout}]{get_bbox()};{body}'


class Overpass:
    def __init__(self, state: State):
        self.state = state

        self.base_url = 'https://overpass.monicz.dev/api/interpreter'
        self.c = get_http_client()

    def get_timestamp_osm_base(self) -> int:
        timeout = 30
        query = f'[out:json][timeout:{timeout}];'

        r = self.c.post(self.base_url, data={'data': query}, timeout=timeout * 2)
        r.raise_for_status()

        data = r.json()
        return parse_timestamp(data['osm3s']['timestamp_osm_base'])

    def query(self) -> list[OverpassEntry] | bool:
        if self.state.start_ts == self.state.end_ts:
            return False

        timeout = 300
        query = build_query(self.state.start_ts, self.state.end_ts, timeout=timeout)

        r = self.c.post(self.base_url, data={'data': query}, timeout=timeout * 2)
        r.raise_for_status()

        data = r.json()['elements']
        data = (e for e in data if any(t.startswith('addr:') for t in e.get('tags', [])))
        result = []

        for e in data:
            if e['type'] == 'node':
                lat, lon = e['lat'], e['lon']

                e['bounds'] = {
                    'minlat': lat,
                    'minlon': lon,
                    'maxlat': lat,
                    'maxlon': lon,
                }

            bb_min = Point(e['bounds']['minlat'], e['bounds']['minlon'])
            bb_max = Point(e['bounds']['maxlat'], e['bounds']['maxlon'])
            bb_size = Size(
                width=distance(bb_min, Point(bb_min.lat, bb_max.lon)).meters,
                height=distance(bb_min, Point(bb_max.lat, bb_min.lon)).meters
            )

            entry = OverpassEntry(
                timestamp=e['timestamp'],
                changeset_id=e['changeset'],
                element_type=e['type'],
                element_id=e['id'],
                tags=e['tags'],
                nodes=e.get('nodes', []),
                bb_min=bb_min,
                bb_max=bb_max,
                bb_size=bb_size,
            )

            if self.state.start_ts <= entry.timestamp <= self.state.end_ts:
                result.append(entry)

        return result

    @skip_large()
    @batch()
    def query_duplicates(self, raw_issues: list[OverpassEntry]) -> list[OverpassEntry]:
        issues = [i for i in raw_issues if check_whitelist(i.tags)]

        if not issues:
            return []

        timeout = 300
        query = build_duplicates_query(issues, timeout=timeout)

        r = self.c.post(self.base_url, data={'data': query}, timeout=timeout * 2)
        r.raise_for_status()

        data = r.json()['elements']
        data_iter = iter(data)
        result = set(issues)

        for issue in issues:
            ref_n = []
            ref_wr = []

            for e in data_iter:
                if e['type'] == 'count':
                    assert int(e['tags']['total']) == len(ref_n) + len(ref_wr)
                    break

                entry = OverpassEntry(
                    # treat as the same changeset for simpler code
                    timestamp=issue.timestamp,
                    changeset_id=issue.changeset_id,
                    element_type=e['type'],
                    element_id=e['id'],
                    tags=e['tags'],
                    nodes=e.get('nodes', []),
                    bb_min=Point(0, 0),
                    bb_max=Point(0, 0),
                    bb_size=(0, 0),
                )

                if e['type'] == 'node':
                    ref_n.append(entry)
                else:
                    ref_wr.append(entry)

            else:
                raise

            ref_duplicates = duplicate_search(issue, ref_n, ref_wr)

            if ref_duplicates:
                result.update(ref_duplicates)
            else:
                result.remove(issue)

        return list(result)

    @skip_large()
    @batch()
    def query_place_not_in_area(self, issues: list[OverpassEntry]) -> list[OverpassEntry]:
        timeout = 300
        query = build_place_not_in_area_query(issues, timeout=timeout)

        r = self.c.post(self.base_url, data={'data': query}, timeout=timeout * 2)
        r.raise_for_status()

        data = r.json()['elements']
        data_iter = iter(data)
        result = []

        for issue in issues:
            read_size = 0
            place_ok = False

            for e in data_iter:
                # check for end of section
                if e['type'] == 'count':
                    assert int(e['tags']['total']) == read_size
                    break

                read_size += 1
                place_ok = True
            else:
                raise

            if not place_ok:
                result.append(issue)

        return result

    @batch()
    def query_place_mistype(self, issues: list[OverpassEntry]) -> list[OverpassEntry]:
        timeout = 300
        query = build_place_mistype_query(issues, timeout=timeout)

        r = self.c.post(self.base_url, data={'data': query}, timeout=timeout * 2)
        r.raise_for_status()

        data = r.json()['elements']
        data_iter = iter(data)
        result = []

        for issue in issues:
            read_size = 0
            is_in = set()

            for e in data_iter:
                # check for end of section
                if e['type'] == 'count':
                    assert int(e['tags']['total']) == read_size
                    break

                read_size += 1

                for key in ('name', 'alt_name'):
                    if val := e['tags'].get(key, None):
                        is_in.add(val)
            else:
                raise

            if issue.tags['addr:place'] not in is_in:
                addr_place_norm = normalize(issue.tags['addr:place'])

                if any(addr_place_norm == normalize(i) for i in is_in):
                    result.append(issue)

        return result

    @skip_large()
    @batch()
    @tier(500, 1000, 3000)
    def query_street_names(self, issues: list[OverpassEntry], *, tier: int) -> list[OverpassEntry]:
        timeout = 300
        query = build_street_names_query(issues, timeout=timeout, around=tier)

        r = self.c.post(self.base_url, data={'data': query}, timeout=timeout * 2)
        r.raise_for_status()

        data = r.json()['elements']
        data_iter = iter(data)
        result = []

        for issue in issues:
            read_size = 0
            street_names = set()

            for e in data_iter:
                # check for end of section
                if e['type'] == 'count':
                    assert int(e['tags']['total']) == read_size
                    break

                read_size += 1

                for key in ('name', 'alt_name'):
                    if val := e['tags'].get(key, None):
                        street_names.add(val)
            else:
                raise

            if issue.tags['addr:street'] not in street_names:
                result.append(issue)

        return result

    def is_editing_tags(self, cat: Category, issues: dict[Check, list[OverpassEntry]]) -> bool:
        timeout = 300
        partitions: dict[int, set[OverpassEntry]] = defaultdict(set)
        entry_map: dict[ElementType, dict[int, tuple[Check, OverpassEntry]]] = defaultdict(dict)

        for check, entries in issues.items():
            for entry in entries:
                partitions[entry.timestamp].add(entry)
                entry_map[entry.element_type][entry.element_id] = (check, entry)

        for partition_time, partition_issues in partitions.items():
            partition_query = build_partition_query(partition_time, list(partition_issues), timeout=timeout)

            r = self.c.post(self.base_url, data={'data': partition_query}, timeout=timeout * 2)
            r.raise_for_status()

            elements = r.json()['elements']

            # fewer elements means some were created
            if len(elements) < len(partition_issues):
                return True

            if len(elements) > len(partition_issues):
                raise

            for element in elements:
                ref_check, ref_entry = entry_map[element['type']][element['id']]
                tags_diff: Tags = {k: v for k, v in set(ref_entry.tags.items()) - set(element.get('tags', {}).items())}

                # selector by category group if set
                if cat.selectors:
                    if cat.is_selected(tags_diff):
                        return True
                else:
                    if ref_check.is_selected(tags_diff):
                        return True

        return False
