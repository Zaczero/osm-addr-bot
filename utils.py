import functools

from requests import Session

from config import USER_AGENT


def get_http_client(*, auth: tuple | None = None, headers: dict | None = None) -> Session:
    if not headers:
        headers = {}

    s = Session()
    s.auth = auth
    s.headers.update({'User-Agent': USER_AGENT} | headers)
    s.request = functools.partial(s.request, timeout=30)

    return s
