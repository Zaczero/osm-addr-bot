from dataclasses import dataclass

from utils import parse_timestamp

UID_OFFSET = 1 << 27


@dataclass(slots=True, kw_only=True)
class OverpassEntry:
    timestamp: int
    changeset_id: int
    element_type: str
    element_id: int
    tags: dict[str, str]
    nodes: list[int]
    _uid: int = 0

    # noinspection PyTypeChecker
    def __post_init__(self):
        if isinstance(self.timestamp, str):
            self.timestamp = parse_timestamp(self.timestamp)

        self.changeset_id = int(self.changeset_id)
        self.element_id = int(self.element_id)

        if self.element_type == 'node':
            self._uid = -self.element_id
        elif self.element_type == 'way':
            self._uid = self.element_id + UID_OFFSET
        else:  # relation
            assert self.element_id < UID_OFFSET, 'Increase uid offset'
            self._uid = self.element_id

    def __hash__(self):
        return self._uid

    def __eq__(self, other):
        if isinstance(other, OverpassEntry):
            return self._uid == other._uid

        return NotImplemented
