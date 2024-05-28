import os
from pathlib import Path

OSM_TOKEN = os.getenv('OSM_TOKEN')
DRY_RUN = os.getenv('DRY_RUN') == '1'
IGNORE_ALREADY_DISCUSSED = os.getenv('IGNORE_ALREADY_DISCUSSED') == '1'

# Dedicated instance unavailable? Pick one from the public list:
# https://wiki.openstreetmap.org/wiki/Overpass_API#Public_Overpass_API_instances
OVERPASS_API_INTERPRETER = os.getenv('OVERPASS_API_INTERPRETER', 'https://overpass.monicz.dev/api/interpreter')

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

    'osm-revert',

    # fallback, general blacklist
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

NEW_USER_THRESHOLD = 15
PRO_USER_THRESHOLD = 800

DUPLICATE_FALSE_POSITIVE_MAX_DIST = 2  # max 1 object separation
DUPLICATE_BFS_EXCLUDE_ADDR = True

LARGE_ELEMENT_MAX_SIZE = 1000  # meters

MAX_ISSUES_PER_CHANGESET = 100
