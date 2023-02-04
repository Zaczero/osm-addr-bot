import json
from dataclasses import asdict
from time import time

from check import Check
from checks import ALL_CHECKS
from config import STATE_PATH, STATE_MAX_BACKLOG, STATE_MAX_DIFF
from overpass_entry import OverpassEntry


class State:
    start_ts: int
    end_ts: int
    _rescheduled_issues: dict[int, dict[str, list[dict]]]

    def __enter__(self):
        if not STATE_PATH.exists():
            with open(STATE_PATH, 'x') as f:
                f.write('0')

        # open for rw to ensure permissions
        with open(STATE_PATH, 'r+') as f:
            try:
                data = json.load(f)
                assert isinstance(data, dict)
            except Exception:
                f.seek(0)
                data = {
                    'state': int(f.read().strip()),
                    'rescheduled_issues': {}
                }

        state = data['state']
        now = int(time())

        self.start_ts = max(now - STATE_MAX_BACKLOG, state)
        self.end_ts = self.start_ts
        self._rescheduled_issues = data['rescheduled_issues']

        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass

    def configure_end_ts(self, value: int) -> None:
        self.end_ts = value

        if self.end_ts - self.start_ts > STATE_MAX_DIFF:
            self.end_ts = self.start_ts + STATE_MAX_DIFF

    def merge_rescheduled_issues(self, issues: dict[int, dict[Check, list[OverpassEntry]]]) -> int:
        for changeset_id, changeset_issues in self._rescheduled_issues.items():
            changeset_id = int(changeset_id)

            for check_identifier, check_issues_d in changeset_issues.items():
                check = next(c for c in ALL_CHECKS if c.identifier == check_identifier)
                check_issues = [OverpassEntry(**d) for d in check_issues_d]
                assert all(i.timestamp <= self.start_ts for i in check_issues)
                issues[changeset_id][check].extend(check_issues)

        merged = len(self._rescheduled_issues)
        self._rescheduled_issues = {}
        return merged

    def reschedule_issues(self, changeset_id: int, changeset_issues: dict[Check, list[OverpassEntry]]) -> None:
        self._rescheduled_issues.setdefault(changeset_id, {})

        for check, check_issues in changeset_issues.items():
            self._rescheduled_issues[changeset_id] \
                .setdefault(check.identifier, []) \
                .extend(asdict(i) for i in check_issues)

    def write_state(self):
        with open(STATE_PATH, 'w') as f:
            json.dump({
                'state': self.end_ts,
                'rescheduled_issues': self._rescheduled_issues
            }, f, indent=2)
