from datetime import datetime

import xmltodict

from checks import Check
from config import SEARCH_BBOX, SEARCH_RELATION
from overpass_entry import OverpassEntry
from state import State
from utils import get_http_client


def parse_timestamp(ts: str) -> int:
    date_format = '%Y-%m-%dT%H:%M:%SZ'
    return int(datetime.strptime(ts, date_format).timestamp())


def format_timestamp(ts: int) -> str:
    date_format = '%Y-%m-%dT%H:%M:%SZ'
    return datetime.utcfromtimestamp(ts).strftime(date_format)


def get_bbox() -> str:
    e = SEARCH_BBOX
    min_lat, max_lat = e['min_lat'], e['max_lat']
    min_lon, max_lon = e['min_lon'], e['max_lon']
    return f'[bbox:{min_lat},{min_lon},{max_lat},{max_lon}]'


def build_query(start_ts: int, end_ts: int, check: Check, timeout: int) -> str:
    assert start_ts < end_ts
    start = format_timestamp(start_ts)
    end = format_timestamp(end_ts)

    return f'[out:csv(::changeset,::type,::id;false)][timeout:{timeout}]{get_bbox()};' \
           f'relation(id:{SEARCH_RELATION});map_to_area;' \
           f'(' \
           f'nwr{check.overpass}(changed:"{start}","{end}")(area._);' \
           f');' \
           f'out meta;'


class Overpass:
    def __init__(self, state: State):
        self.state = state

        self.base_url = 'https://overpass.monicz.dev/api/interpreter'
        self.c = get_http_client()

    def is_up_to_date(self, end_ts: int) -> bool:
        r = self.c.post(self.base_url, data={'data': '[out:json][timeout:15];'})
        r.raise_for_status()

        data = r.json()
        overpass_ts = parse_timestamp(data['osm3s']['timestamp_osm_base'])

        return end_ts < overpass_ts

    def query(self, check: Check) -> list[OverpassEntry]:
        timeout = 300
        query = build_query(self.state.start_ts, self.state.end_ts, check, timeout=timeout)

        r = self.c.post(self.base_url, data={'data': query}, timeout=timeout)
        r.raise_for_status()

        return [OverpassEntry(*(row.split('\t')), reason=check) for row in r.text.split('\n') if row]
