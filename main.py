import time
from datetime import datetime

from tqdm import tqdm

from checks import Check, ALL_CHECKS
from config import NEW_USER_THRESHOLD, PRO_USER_THRESHOLD, DRY_RUN
from osmapi import OsmApi
from overpass import Overpass
from overpass_entry import OverpassEntry
from state import State

LINK_SORT_DICT = {
    'node': 0,
    'way': 1,
    'relation': 2
}


def should_discuss(changeset: dict) -> bool:
    changeset_id = changeset['id']

    if changeset['open']:
        print(f'🔓️ Skipped {changeset_id}: Open changeset')
        return False

    if changeset['changes_count'] > 2500:
        print(f'🤖 Skipped {changeset_id}: Possible import')
        return False

    if changeset['tags'].get('created_by', None).startswith('StreetComplete'):
        print(f'🌆 Skipped {changeset_id}: StreetComplete')
        return False

    for discussion in changeset.get('discussion', []):
        if discussion['uid'] == changeset['uid']:
            continue

        # noinspection SpellCheckingInspection
        if any(word in discussion['text'] for word in ('addr', 'adres')):
            print(f'🗨️ Skipped {changeset_id}: Already discussed')
            return False

    return True


# noinspection SpellCheckingInspection
def compose_message(user: dict, issues: dict[Check, list[OverpassEntry]]) -> str:
    new_user = user['changesets']['count'] <= NEW_USER_THRESHOLD
    pro_user = user['changesets']['count'] >= PRO_USER_THRESHOLD

    message = ''

    if new_user:
        message += '🗺️ Witaj na OpenStreetMap!\n\n'

    message += 'Zauważyłem, że twoja zmiana zawiera niepoprawne adresy. ' \
               'Przygotowałem listę obiektów do poprawy oraz dodatkowe informacje:\n\n'

    for check, entries in issues.items():
        if pro_user:
            message += check.message + '\n'
        else:
            message += check.message + ' ' + check.message_fix + '\n'

        for entry in sorted(entries, key=lambda e: LINK_SORT_DICT[e.element_type]):
            assert isinstance(entry, OverpassEntry)
            message += f'https://www.openstreetmap.org/{entry.element_type}/{entry.element_id}\n'

        message += '\n'

    if pro_user:
        message += 'Pozdrawiam! 🦀'
    else:
        message += 'Dokumentacja adresów:\n' \
                   'https://wiki.openstreetmap.org/wiki/Pl:Key:addr:*\n' \
                   '\n' \
                   'W razie problemów lub pytań, proszę pisać. Chętnie pomogę.\n' \
                   'Pozdrawiam! 🦀'

    return message


def main():
    print('🔒️ Logging in to OpenStreetMap')
    osm = OsmApi()
    user = osm.get_authorized_user()
    print(f'👤 Welcome, {user["display_name"]}!')

    with State() as s:
        print(f'Time range: {datetime.utcfromtimestamp(s.start_ts)} - {datetime.utcfromtimestamp(s.end_ts)}')

        overpass = Overpass(s)

        if not overpass.is_up_to_date(s.end_ts):
            print('🕒️ Overpass is updating, please try again shortly')
            return

        issues: dict[int, dict[Check, list[OverpassEntry]]] = {}

        for check in tqdm(ALL_CHECKS, desc='Querying issues'):
            for i in overpass.query(check):
                issues \
                    .setdefault(i.changeset_id, {}) \
                    .setdefault(i.reason, []) \
                    .append(i)

        print(f'Total changesets: {len(issues)}')

        for changeset_id, changeset_issues in issues.items():
            changeset = osm.get_changeset(changeset_id)

            if not should_discuss(changeset):
                continue

            user = osm.get_user(changeset['uid'])

            # deleted users will not read the discussion
            if user is None:
                continue

            message = compose_message(user, changeset_issues)

            if not DRY_RUN:
                osm.post_comment(changeset_id, message)
                print(f'✅ Notified {changeset_id}')
            else:
                print(f'✅ Notified {changeset_id} [DRY_RUN]')

        if not DRY_RUN:
            s.update_state()


if __name__ == '__main__':
    main()
