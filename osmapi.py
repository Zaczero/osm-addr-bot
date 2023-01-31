from tenacity import retry, stop_after_attempt, wait_exponential

from config import OSM_USERNAME, OSM_PASSWORD
from utils import get_http_client


class OsmApi:
    def __init__(self):
        self.base_url = 'https://api.openstreetmap.org/api/0.6'
        self.c = get_http_client(auth=(OSM_USERNAME, OSM_PASSWORD))

    def get_authorized_user(self) -> dict:
        r = self.c.get(f'{self.base_url}/user/details.json')
        r.raise_for_status()

        return r.json()['user']

    @retry(stop=stop_after_attempt(5), wait=wait_exponential())
    def get_changeset(self, changeset_id: int) -> dict:
        r = self.c.get(f'{self.base_url}/changeset/{changeset_id}.json?include_discussion=true')
        r.raise_for_status()

        return r.json()['elements'][0]

    @retry(stop=stop_after_attempt(5), wait=wait_exponential())
    def get_user(self, user_id: int) -> dict | None:
        r = self.c.get(f'{self.base_url}/user/{user_id}.json')

        if r.status_code == 404:
            return None

        r.raise_for_status()

        return r.json()['user']

    @retry(stop=stop_after_attempt(5), wait=wait_exponential())
    def post_comment(self, changeset_id: int, message: str) -> None:
        r = self.c.post(f'{self.base_url}/changeset/{changeset_id}/comment', data={
            'text': message
        })
        r.raise_for_status()
