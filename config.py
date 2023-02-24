import os
from pathlib import Path

OSM_USERNAME = os.getenv('OSM_USERNAME')
OSM_PASSWORD = os.getenv('OSM_PASSWORD')
DRY_RUN = os.getenv('DRY_RUN', None) == '1'
IGNORE_ALREADY_DISCUSSED = os.getenv('IGNORE_ALREADY_DISCUSSED', None) == '1'

USER_AGENT = f'osm-addr-bot (+https://github.com/Zaczero/osm-addr-bot)'

APP_BLACKLIST = (
    'StreetComplete',
    'Every Door',
    'OsmAnd',
    'Organic Maps',
    'MAPS.ME',

    'OsmHydrant',
    'aed.openstreetmap.org.pl',
    'openaedmap.org',

    # backup, general blacklist
    'Android',
    'iOS',
)

SEARCH_RELATION = 49715
SEARCH_BBOX = {
    'min_lat': 49.0273953,
    'min_lon': 14.0745211,
    'max_lat': 54.8515360,
    'max_lon': 24.0299858
}

STATE_PATH = Path('state.txt')

# auto upgrade file type for new users
if not STATE_PATH.exists():
    STATE_PATH = Path('state.json')

STATE_MAX_BACKLOG = 3600 * 24 * 3  # 3 days
STATE_MAX_DIFF = 3600 * 8  # 8 hours

NEW_USER_THRESHOLD = 12
PRO_USER_THRESHOLD = 600

DUPLICATE_FALSE_POSITIVE_MAX_DIST = 2  # max 1 object separation
DUPLICATE_BFS_EXCLUDE_ADDR = True

# those people do not deserve to be greeted
NOT_NICE_USERS = {
    # 123123123
}

SUMMARY_MIN_EDIT_DELAY = 3600 * 24 * 2  # 2 days
SUMMARY_MIN_RSS_DELAY = 3600 * 3  # 3 hours
SUMMARY_MAX_RSS_HISTORY = (24 / 3) * 14

LARGE_ELEMENT_MAX_SIZE = 1000  # meters
