import fcntl
import json
from dataclasses import asdict
from time import time
from typing import IO

from aliases import Identifier
from check import Check
from checks import ALL_CHECKS
from config import STATE_MAX_BACKLOG, STATE_MAX_DIFF, STATE_PATH
from overpass_entry import OverpassEntry


class State:
    start_ts: int
    end_ts: int
    _rescheduled_issues: dict[Identifier, dict[int, dict[str, list[dict]]]]
    _fd: IO

    def __enter__(self):
        if not STATE_PATH.exists():
            with open(STATE_PATH, 'x') as f:
                f.write('0')

        # open for rw to ensure permissions
        self._fd = open(STATE_PATH, 'r+')
        fcntl.flock(self._fd, fcntl.LOCK_EX | fcntl.LOCK_NB)

        try:
            data = json.load(self._fd)
            assert isinstance(data, dict)
        except Exception:
            self._fd.seek(0)
            data = {'state': int(self._fd.read().strip())}

        state = data['state']
        now = int(time())

        self.start_ts = max(now - STATE_MAX_BACKLOG, state)
        self.end_ts = self.start_ts
        self._rescheduled_issues = data.get('rescheduled_issues', {})

        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._fd.close()

    def configure_end_ts(self, value: int) -> None:
        self.end_ts = value

        if self.end_ts - self.start_ts > STATE_MAX_DIFF:
            self.end_ts = self.start_ts + STATE_MAX_DIFF

    def merge_rescheduled_issues(self, cat: Identifier, issues: dict[int, dict[Check, list[OverpassEntry]]]) -> int:
        cat_issues = self._rescheduled_issues.get(cat, {})

        for changeset_id, changeset_issues in cat_issues.items():
            changeset_id = int(changeset_id)

            for check_identifier, check_issues_d in changeset_issues.items():
                check = next(c for c in ALL_CHECKS if c.identifier == check_identifier)
                check_issues = [OverpassEntry(**d) for d in check_issues_d]
                assert all(i.timestamp <= self.start_ts for i in check_issues)
                issues[changeset_id][check].extend(check_issues)

        self._rescheduled_issues[cat] = {}
        return len(cat_issues)

    def reschedule_issues(self, cat: Identifier, changeset_id: int, issues: dict[Check, list[OverpassEntry]]) -> None:
        self._rescheduled_issues.setdefault(cat, {})
        self._rescheduled_issues[cat].setdefault(changeset_id, {})

        for check, check_issues in issues.items():
            assert all(changeset_id == i.changeset_id for i in check_issues)
            self._rescheduled_issues[cat][changeset_id] \
                .setdefault(check.identifier, []) \
                .extend(asdict(i) for i in check_issues)

    # TODO:
    # def add_to_summary(self, changeset_id: int, issues: dict[Check, list[OverpassEntry]]) -> None:
    #     self._summary.setdefault(changeset_id, {})
    #
    #     for check, check_issues in issues.items():
    #         assert all(changeset_id == i.changeset_id for i in check_issues)
    #         self._summary[changeset_id] \
    #             .setdefault(check.identifier, []) \
    #             .extend(asdict(i) for i in check_issues)

    def write_state(self):
        self._fd.seek(0)
        self._fd.truncate(0)

        json.dump({
            'state': self.end_ts,
            'rescheduled_issues': self._rescheduled_issues
        }, self._fd, indent=2)
