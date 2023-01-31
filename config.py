import os
from pathlib import Path

OSM_USERNAME = os.getenv('OSM_USERNAME')
OSM_PASSWORD = os.getenv('OSM_PASSWORD')

USER_AGENT = f'osm-addr-bot (+https://github.com/Zaczero/osm-addr-bot)'

SEARCH_RELATION = 49715
SEARCH_BBOX = {
    'min_lat': 49.0273953,
    'min_lon': 14.0745211,
    'max_lat': 54.8515360,
    'max_lon': 24.0299858
}

STATE_PATH = Path('state.txt')
STATE_MAX_BACKLOG = 3600 * 24 * 3  # 3 days
STATE_MAX_DIFF = 3600 * 8  # 8 hours
STATE_MIN_DELAY = 60 * 5  # 5 minutes

NEW_USER_THRESHOLD = 12
PRO_USER_THRESHOLD = 600
