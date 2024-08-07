import functools
import re
from collections import defaultdict
from datetime import UTC, datetime, timezone

from requests import Session

from check import Check
from config import USER_AGENT
from overpass_entry import OverpassEntry


def get_http_client(*, headers: dict | None = None) -> Session:
    if not headers:
        headers = {}

    s = Session()
    s.headers.update({'User-Agent': USER_AGENT, **headers})
    s.request = functools.partial(s.request, timeout=30)
    return s


def parse_timestamp(ts: str) -> int:
    date_format = '%Y-%m-%dT%H:%M:%SZ'
    return int(datetime.strptime(ts, date_format).replace(tzinfo=timezone.utc).timestamp())


def format_timestamp(ts: int) -> str:
    date_format = '%Y-%m-%dT%H:%M:%SZ'
    return datetime.fromtimestamp(ts, UTC).strftime(date_format)


ESCAPE_TABLE = str.maketrans({
    '"': '\\"',
    '\\': '\\\\'
})


def escape_overpass(unsafe: str) -> str:
    return unsafe.translate(ESCAPE_TABLE)


MULTIPLE_SPACE_RE = re.compile(r'\s{2,}')


def normalize(a: str) -> str:
    return MULTIPLE_SPACE_RE.sub(' ', a.strip().lower())


def group_by_changeset(issues: dict[Check, list[OverpassEntry]]) -> dict[int, dict[Check, list[OverpassEntry]]]:
    grouped = defaultdict(lambda: defaultdict(list))

    for check, check_issues in issues.items():
        for i in check_issues:
            grouped[i.changeset_id][check].append(i)

    return grouped
