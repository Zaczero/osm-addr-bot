import time
from collections import defaultdict
from datetime import datetime

from check import Check
from checks import ALL_CHECKS
from config import NEW_USER_THRESHOLD, PRO_USER_THRESHOLD, DRY_RUN, APP_BLACKLIST, IGNORE_ALREADY_DISCUSSED, \
    NOT_NICE_USERS
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
    created_by = changeset['tags'].get('created_by', '')

    if any(black.lower() in created_by.lower() for black in APP_BLACKLIST):
        print(f'📵 Skipped {changeset_id}: {created_by}')
        return False

    for discussion in changeset.get('discussion', []):
        if discussion['uid'] == changeset['uid']:
            continue

        # noinspection SpellCheckingInspection
        if any(word in discussion['text'] for word in ('addr', 'adres')):
            if not IGNORE_ALREADY_DISCUSSED:
                print(f'💬 Skipped {changeset_id}: Already discussed')
                return False
            else:
                print(f'💬 Skipped {changeset_id}: Already discussed [IGNORED]')
                break

    return True


def filter_should_not_discuss(osm: OsmApi, issues: dict[Check, list[OverpassEntry]]) -> None:
    changeset_ids = set(i.changeset_id for ii in issues.values() for i in ii)

    print(f'[2/?] Filtering {len(changeset_ids)} changeset{"" if len(changeset_ids) == 1 else "s"}…')

    for changeset_id in list(changeset_ids):
        changeset = osm.get_changeset(changeset_id)

        if not should_discuss(changeset):
            changeset_ids.remove(changeset_id)

    for check, check_issues in list(issues.items()):
        new_issues = [i for i in check_issues if i.changeset_id in changeset_ids]

        if new_issues:
            issues[check] = new_issues
        else:
            issues.pop(check)


def filter_post_fn(overpass: Overpass, issues: dict[Check, list[OverpassEntry]]) -> None:
    check_post = [(c, i) for c, i in issues.items() if c.post_fn]

    for i, (check, check_issues) in enumerate(check_post):
        print(f'[{3 + i}/{2 + len(check_post)}] Filtering {len(check_issues)} × {check.identifier}…')
        new_issues = check.post_fn(overpass, check_issues)

        if new_issues:
            issues[check] = new_issues
        else:
            issues.pop(check)


def filter_priority(issues: dict[Check, list[OverpassEntry]], *, consider_post_fn: bool) -> None:
    max_priorities = {}

    for check, check_issues in sorted(issues.items(), key=lambda t: t[0].priority, reverse=True):
        new_issues = []

        for check_issue in check_issues:
            if max_priorities.get(check_issue, 0) <= check.priority:

                if not consider_post_fn or check.post_fn is None:
                    max_priorities[check_issue] = check.priority

                new_issues.append(check_issue)

        if new_issues:
            issues[check] = new_issues
        else:
            issues.pop(check)


# noinspection SpellCheckingInspection
def compose_message(user: dict, issues: dict[Check, list[OverpassEntry]]) -> str:
    new_user = user['changesets']['count'] <= NEW_USER_THRESHOLD
    pro_user = user['changesets']['count'] >= PRO_USER_THRESHOLD

    message = ''

    if new_user:
        message += '🗺️ Witaj na OpenStreetMap!\n\n'

    if pro_user:
        message += 'Zauważyłem, że Twoja zmiana zawiera niepoprawne adresy. ' \
                   'Przygotowałem listę obiektów oraz dodatkowe informacje:\n\n'
    else:
        message += 'Zauważyłem, że Twoja zmiana zawiera niepoprawne adresy. ' \
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

    if user['id'] in NOT_NICE_USERS:
        message = message.strip()
    elif pro_user:
        message += 'Pozdrawiam! 🦀'
    else:
        message += 'Dokumentacja adresów (po polsku):\n' \
                   'https://wiki.openstreetmap.org/wiki/Pl:Key:addr:*\n' \
                   '\n' \
                   'W razie problemów lub pytań, proszę pisać. Chętnie pomogę.\n' \
                   'Pozdrawiam! 🦀'

    return message


def main():
    time_start = time.perf_counter()

    if DRY_RUN:
        print('🌵 This is a dry run')

    print('🔒️ Logging in to OpenStreetMap')
    osm = OsmApi()
    user = osm.get_authorized_user()
    print(f'👤 Welcome, {user["display_name"]}!')

    with State() as s:
        overpass = Overpass(s)
        s.configure_end_ts(overpass.get_timestamp_osm_base() - 1)

        print(f'Time range: {datetime.utcfromtimestamp(s.start_ts)} - {datetime.utcfromtimestamp(s.end_ts)}')
        print(f'[1/?] Querying issues…')
        queried = overpass.query(ALL_CHECKS)

        if queried is False:
            print('🕒️ Overpass is updating, try again shortly')
            return

        filter_should_not_discuss(osm, queried)
        filter_priority(queried, consider_post_fn=True)
        filter_post_fn(overpass, queried)

        issues: dict[int, dict[Check, list[OverpassEntry]]] = defaultdict(lambda: defaultdict(list))

        for check, check_issues in queried.items():
            for i in check_issues:
                issues[i.changeset_id][check].append(i)

        queried_len = len(issues)
        merged_len = s.merge_rescheduled_issues(issues)

        if merged_len:
            print(f'Total changesets: {queried_len}+{merged_len}')
        else:
            print(f'Total changesets: {queried_len}')

        for changeset_id, changeset_issues in issues.items():
            changeset = osm.get_changeset(changeset_id)

            if changeset['open']:
                print(f'🔓️ Rescheduled {changeset_id}: Open changeset')
                s.reschedule_issues(changeset_id, changeset_issues)
                continue

            # this must be done after post_fn - issues may change because of it
            if not overpass.is_editing_address(changeset_issues):
                print(f'🏡 Skipped {changeset_id}: Not editing addresses')
                continue

            filter_priority(changeset_issues, consider_post_fn=False)

            user = osm.get_user(changeset['uid'])

            # deleted users will not read the discussion
            if user is None:
                print(f'❌ Skipped {changeset_id}: User not found')
                continue

            message = compose_message(user, changeset_issues)

            if not DRY_RUN:
                osm.post_comment(changeset_id, message)
                print(f'✅ Notified https://www.openstreetmap.org/changeset/{changeset_id}')
            else:
                print(message)
                print(f'✅ Notified https://www.openstreetmap.org/changeset/{changeset_id} [DRY_RUN]')

            s.schedule_for_summary(changeset_issues)

        if not DRY_RUN:
            s.write_state()

    print(f'🏁 Finished in {time.perf_counter() - time_start:.1F} sec')
    print()


if __name__ == '__main__':
    main()
