import time
from datetime import datetime
from itertools import chain

from cachetools import cached
from cachetools.keys import hashkey

from category import Category
from check import Check
from checks import OVERPASS_CATEGORIES
from config import (APP_BLACKLIST, DRY_RUN, IGNORE_ALREADY_DISCUSSED,
                    NEW_USER_THRESHOLD, NOT_NICE_USERS, PRO_USER_THRESHOLD)
from osmapi import OsmApi
from overpass import Overpass
from overpass_entry import OverpassEntry
from state import State
from utils import group_by_changeset

LINK_SORT_DICT = {
    'node': 0,
    'way': 1,
    'relation': 2
}


@cached(cache={}, key=lambda osm, changeset_id: hashkey(changeset_id))
def should_discuss(osm: OsmApi, changeset_id: int) -> bool:
    changeset = osm.get_changeset(changeset_id)
    changeset_id = changeset['id']
    created_by = changeset['tags'].get('created_by', '')

    if any(black.lower() in created_by.lower() for black in APP_BLACKLIST):
        print(f'📵 Skipped {changeset_id}: {created_by}')
        return False

    for discussion in changeset.get('discussion', []):
        if discussion['uid'] == changeset['uid']:
            continue

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
        if not should_discuss(osm, changeset_id):
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
        print(f'[{3 + i}/{2 + len(check_post)}] Filtering {len(check_issues)} × {check.identifier}…', end='')

        time_start = time.perf_counter()
        new_issues = check.post_fn(overpass, check_issues)
        print(f' ({time.perf_counter() - time_start:.1F} sec)')

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


def compose_message(cat: Category, user: dict, issues: dict[Check, list[OverpassEntry]]) -> str:
    new_user = user['changesets']['count'] <= NEW_USER_THRESHOLD
    pro_user = user['changesets']['count'] >= PRO_USER_THRESHOLD

    message = ''

    # header
    if new_user:
        message += '🗺️ Witaj na OpenStreetMap!\n\n'

    is_critical = any(c.critical for c in issues)

    header = cat.header_critical if is_critical else cat.header
    assert not header.endswith('\n')
    message += header
    message += '\n\n'

    # body
    for check, entries in issues.items():
        assert entries
        assert not check.desc.endswith('\n')
        assert (check.extra is None) or (not check.extra.endswith('\n'))

        if pro_user or (check.extra is None):
            message += check.desc + '\n'
        else:
            message += check.desc + ' ' + check.extra + '\n'

        for entry in sorted(entries, key=lambda e: LINK_SORT_DICT[e.element_type]):
            assert isinstance(entry, OverpassEntry)
            message += f'https://www.openstreetmap.org/{entry.element_type}/{entry.element_id}\n'

        message += '\n'

    # footer
    docs = list(filter(None, chain([cat.docs], (c.docs for c in issues))))

    assert all((d is None) or (not d.endswith('\n')) for d in docs)

    if pro_user or (docs is None):
        pass
    else:
        message += '\n'.join(docs)
        message += '\n\n'

    if user['id'] in NOT_NICE_USERS:
        message = message.strip()
    elif pro_user:
        message += 'Pozdrawiam! 🦀'
    else:
        message += 'W razie problemów lub pytań, proszę pisać. Chętnie pomogę.\n' \
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
        changed = overpass.query()

        if changed is False:
            print('🕒️ Overpass is updating, try again shortly')
            return

        assert isinstance(changed, list)

        # TODO: fix progress numbering
        for cat in OVERPASS_CATEGORIES:
            print(f'📂 Category: {cat.identifier}')

            subset = cat.map_checks(changed)

            filter_should_not_discuss(osm, subset)
            filter_priority(subset, consider_post_fn=True)
            filter_post_fn(overpass, subset)

            groups = group_by_changeset(subset)
            discovered_len = len(groups)
            merged_len = s.merge_rescheduled_issues(groups)

            if merged_len:
                print(f'Total changesets: {discovered_len}+{merged_len}')
            else:
                print(f'Total changesets: {discovered_len}')

            for changeset_id, changeset_issues in groups.items():
                changeset = osm.get_changeset(changeset_id)

                if changeset['open']:
                    print(f'🔓️ Rescheduled {changeset_id}: Open changeset')
                    s.reschedule_issues(changeset_id, changeset_issues)
                    continue

                # this must be done after post_fn - issues may change because of it
                if not overpass.is_editing_tags(cat, changeset_issues):
                    print(f'😇 Skipped {changeset_id}: Not guilty')
                    continue

                filter_priority(changeset_issues, consider_post_fn=False)

                user = osm.get_user(changeset['uid'])

                # deleted users will not read the discussion
                if user is None:
                    print(f'❌ Skipped {changeset_id}: User not found')
                    continue

                message = compose_message(cat, user, changeset_issues)

                if not DRY_RUN:
                    osm.post_comment(changeset_id, message)
                    print(f'✅ Notified https://www.openstreetmap.org/changeset/{changeset_id}')
                else:
                    print(message)
                    print(f'✅ Notified https://www.openstreetmap.org/changeset/{changeset_id} [DRY_RUN]')

                # TODO: s.add_to_summary(changeset_id, changeset_issues)

        if not DRY_RUN:
            s.write_state()

    print(f'🏁 Finished in {time.perf_counter() - time_start:.1F} sec')
    print()


if __name__ == '__main__':
    main()
