from time import time

from config import STATE_PATH, STATE_MIN_DELAY, STATE_MAX_BACKLOG, STATE_MAX_DIFF


class State:
    start_ts: int
    end_ts: int

    def __enter__(self):
        if not STATE_PATH.exists():
            with open(STATE_PATH, 'x') as f:
                f.write('0')

        # open for rw to ensure permissions
        with open(STATE_PATH, 'r+') as f:
            state = int(f.read())
            now = int(time())

            self.start_ts = max(now - STATE_MAX_BACKLOG, state)
            self.end_ts = now - STATE_MIN_DELAY

            if self.end_ts - self.start_ts > STATE_MAX_DIFF:
                self.end_ts = self.start_ts + STATE_MAX_DIFF

        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass

    def update_state(self):
        with open(STATE_PATH, 'w') as f:
            f.write(str(self.end_ts))
